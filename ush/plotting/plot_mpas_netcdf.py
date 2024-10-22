#!/usr/bin/env python3
"""
Script for plotting MPAS input and/or output in native NetCDF format"
"""
import argparse
import copy
import glob
import logging
import os
import sys
import time

import uxarray as ux
import matplotlib.pyplot as plt

import uwtools.api.config as uwconfig

def load_dataset(fn: str, gf: str = "") -> ux.UxDataset:
    """
    Program loads the dataset from the specified MPAS NetCDF data file
    and grid file and returns it as a ux.UxDataset object. If grid file not specified,
    it is assumed to be the same as the data file.
    """

    logging.info(f"Reading data from {fn}")
    if gf:
        logging.info(f"Reading grid from {gf}")
    else:
        gf=fn
    grid = ux.open_grid(gf)
    logging.debug(grid)

    return ux.open_dataset(gf,fn)

def plotit(config_d: dict,uxds: ux.UxDataset,filepath: str) -> None:
    """
    The main program that makes the plot(s)
    """

    filename=os.path.basename(filepath)
    #filename minus extension
    fnme=os.path.splitext(filename)[0]

    # To plot all variables, call plotit() recursively, trapping errors
    if config_d["data"]["var"]=="all":
        newconf = copy.deepcopy(config_d)
        for var in uxds:
            logging.debug(f"Trying to plot variable {var}")
            newconf["data"]["var"]=[var]
            try:
                plotit(newconf,uxds,filepath)
            except Exception as e:
                logging.warning(f"Could not plot variable {var}")
                logging.warning(f"{type(e).__name__}:")
                logging.warning(e)
    # To plot all levels, call plotit() recursively, trapping errors
    elif config_d["data"]["lev"]=="all":
        newconf = copy.deepcopy(config_d)
        if "nVertLevels" in uxds[newconf["data"]["var"]].dims:
            levs = range(0,len(uxds[newconf["data"]["var"]]["nVertLevels"]))
        else:
            levs = [0]
        for lev in levs:
            logging.debug(f"Trying to plot level {lev} for variable {newconf['data']['var']}")
            newconf["data"]["lev"]=[lev]
            try:
                plotit(newconf,uxds,filepath)
            except Exception as e:
                logging.warning(f"Could not plot variable {newconf['data']['var']}, level {lev}")
                logging.warning(e)

    elif isinstance(config_d["data"]["var"], list):
        start = time.time()
        for var in config_d["data"]["var"]:
            if "n_face" not in uxds[var].dims:
                logging.info(f"Variable {var} not face-centered, skipping")
                continue
            logging.info(f"Plotting variable {var}")
            field=uxds[var]
            # If multiple timesteps in a file, only plot the first for now
            if "Time" in field.dims:
                logging.info("Plotting first time step")
                field=field.isel(Time=0)
            # Parse multiple levels for 3d fields
            # "sliced" is a dictionary of 2d slices of data we will plot. We use a dictionary
            # instead of a list because the levels may not necessarily be contiguous or monotonic
            sliced = {}
            if "nVertLevels" in field.dims:
                if config_d["data"]["lev"]:
                    levs=config_d["data"]["lev"]
                logging.info(f'Plotting vertical level(s) {levs}')
                for lev in levs:
                    sliced[lev]=field.isel(nVertLevels=lev)
            else:
                levs = [0]
                sliced[0]=field

            for lev in levs:
                logging.debug(f"For level {lev}, data slice to plot:\n{sliced[lev]}")
                if config_d["plot"]["periodic_bdy"]:
                    pc=sliced[lev].to_polycollection(periodic_elements='split')
                else:
                    pc=sliced[lev].to_polycollection()

                pc.set_antialiased(False)

                pc.set_cmap(config_d["plot"]["colormap"])

#            logging.info(f"Timer 4 {time.time()-start}")
                fig, ax = plt.subplots(1, 1, figsize=(config_d["plot"]["figwidth"], config_d["plot"]["figheight"]),
                                   dpi=config_d["plot"]["dpi"], constrained_layout=True)
#            logging.info(f"Timer 5 {time.time()-start}")


                ax.set_xlim((config_d["plot"]["lonrange"][0],config_d["plot"]["lonrange"][1]))
                ax.set_ylim((config_d["plot"]["latrange"][0],config_d["plot"]["latrange"][1]))

            # add geographic features
        #    ax.add_feature(cfeature.COASTLINE)
        #    ax.add_feature(cfeature.BORDERS)

            # Create a dict of substitutable patterns to make string substitutions easier
            # using the python string builtin method format_map()
                patterns = {
                    "var": var,
                    "lev": lev,
                    "units": uxds[var].attrs["units"],
                    "varln": uxds[var].attrs["long_name"],
                    "filename": filename,
                    "fnme": fnme,
                    "date": uxds[var].coords['Time'].dt.strftime('%Y-%m-%d').values[0],
                    "time": uxds[var].coords['Time'].dt.strftime('%H:%M:%S').values[0]
                }
    
                coll = ax.add_collection(pc)
    
                plottitle=config_d["plot"]["title"].format_map(patterns)
                plt.title(plottitle, wrap=True)
    
                # Handle colorbar
                if config_d["plot"].get("colorbar"):
                    cb = config_d["plot"]["colorbar"]
                    cbar = plt.colorbar(coll,ax=ax,orientation=cb["orientation"])
                    if cb.get("label"):
                        cbar.set_label(cb["label"].format_map(patterns))
    
                outfile=config_d["plot"]["filename"].format_map(patterns)
                # Make sure any subdirectories exist before we try to write the file
                logging.debug(f"Saving plot {outfile}")
                if os.path.dirname(outfile):
                    os.makedirs(os.path.dirname(outfile),exist_ok=True)
                plt.savefig(outfile)
                plt.close()


    else:
        raise ValueError('Config value data:var must either be a list of variable names or the literal string "all"')


def setup_logging(logfile: str = "log.generate_FV3LAM_wflow", debug: bool = False) -> logging.Logger:
    """
    Sets up logging, printing high-priority (INFO and higher) messages to screen, and printing all
    messages with detailed timing and routine info in the specified text file.

    If debug = True, print all messages to both screen and log file.
    """
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)

    # Create handlers
    console = logging.StreamHandler()
    fh = logging.FileHandler(logfile)

    # Set the log level for each handler
    if debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    fh.setLevel(logging.DEBUG)  # Log DEBUG and above to the file

    formatter = logging.Formatter("%(name)-22s %(levelname)-8s %(message)s")

    # Set format for file handler
    fh = logging.FileHandler(logfile, mode='w')
    fh.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console)
    logger.addHandler(fh)

    logger.debug("Logging set up successfully")

    return logger


def setup_config(config: str, default: str="default_options.yaml") -> dict:
    """
    Function for reading in dictionary of configuration settings, and performing basic checks
    on those settings

    Args:
        config  (str) : The full path of the user config file
        default (str) : The full path of the default config file
        debug   (bool): Enable extra output for debugging
    Returns:
        dict: A dictionary of the configuration settings after applying defaults and user settings,
              as well as some basic consistency checks
    """
    logging.debug(f"Reading defaults file {default}")
    try:
        expt_config = uwconfig.get_yaml_config(config=default)
    except Exception as e:
        logging.critical(e)
        logging.critical(f"Error reading {config}, check above error trace for details")
        sys.exit(1)
    logging.debug(f"Reading options file {config}")
    try:
        user_config = uwconfig.get_yaml_config(config=config)
    except Exception as e:
        logging.critical(e)
        logging.critical(f"Error reading {config}, check above error trace for details")
        sys.exit(1)

    # Update the dict read from defaults file with the dict read from user config file
    expt_config.update_values(user_config)

    # Perform consistency checks
    if not expt_config["data"].get("lev"):
        logging.debug("Level not specified in config, will use level 0 if multiple found")
        expt_config["data"]["lev"]=0

    logging.debug("Expanding references to other variables and Jinja templates")
    expt_config.dereference()
    return expt_config

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Script for plotting MPAS input and/or output in native NetCDF format"
    )
    parser.add_argument('-c', '--config', type=str, default='config_plot.yaml',
                        help='File used to specify plotting options')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Script will be run in debug mode with more verbose output')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


    # Load settings from config file
    expt_config=setup_config(args.config)

    if os.path.isfile(expt_config["data"]["filename"]):
        files = [expt_config["data"]["filename"]]
    elif glob.glob(expt_config["data"]["filename"]):
        files = sorted(glob.glob(expt_config["data"]["filename"]))
    elif isinstance(expt_config["data"]["filename"], list):
        files = expt_config["data"]["filename"]
    else:
        raise FileNotFoundError(f"Invalid filename(s) specified:\n{expt_config['data']['filename']}")

    if not expt_config["data"].get("gridfile"):
        expt_config["data"]["gridfile"]=""

    for f in files:
        # Open specified file and load dataset
        dataset=load_dataset(f,expt_config["data"]["gridfile"])


        # Make the plots!
        plotit(expt_config,dataset,f)
