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
import cartopy.crs as ccrs
import cartopy.feature as cfeature

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
            sliced=uxds[var]
            if "Time" in sliced.dims:
                logging.info("Plotting first time step")
                sliced=sliced.isel(Time=0)
            lev=0
            if "nVertLevels" in sliced.dims:
                if config_d["data"]["lev"]:
                    lev=config_d["data"]["lev"][0]
                logging.debug(f'Plotting vertical level {lev}')
                sliced=sliced.isel(nVertLevels=lev)


#            logging.info(f"Timer 1 {time.time()-start}")
            logging.debug(sliced)
#            logging.info(f"Timer 2 {time.time()-start}")
            pc=sliced.to_polycollection()
#            logging.info(f"Timer 3 {time.time()-start}")

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
                "fnme": fnme
            }

            coll = ax.add_collection(pc)    

            plottitle=config_d["plot"]["title"].format_map(patterns)
            plt.title(plottitle)

            # Handle colorbar
            if config_d["plot"].get("colorbar"):
                cb = config_d["plot"]["colorbar"]
                cbar = plt.colorbar(coll,ax=ax,orientation=cb["orientation"])
                if cb.get("label"):
                    cbar.set_label(cb["label"].format_map(patterns))

            outfile=config_d["plot"]["filename"].format_map(patterns)
            # Make sure any subdirectories exist before we try to write the file
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


def setup_config(config: str) -> dict:
    logging.debug(f"Reading options file {config}")
    try:
        config_d = uwconfig.get_yaml_config(config=config)
    except Exception as e:
        logging.critical(e)
        logging.critical(f"Error reading {config}, check above error trace for details")
        sys.exit(1)
    if not config_d["data"].get("lev"):
        logging.debug(f"Level not specified in config, will use level 0 if multiple found")
        config_d["data"]["lev"]=0

    logging.debug(f"Expanding references to other variables and Jinja templates")
    config_d.dereference()
    return config_d

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Script for plotting MPAS input and/or output in native NetCDF format"
    )
    parser.add_argument('-c', '--config', type=str, default='plot_options.yaml',
                        help='File used to specify plotting options')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Script will be run in debug mode with more verbose output')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


    # Load settings from config file
    confg_d=setup_config(args.config)

    if os.path.isfile(confg_d["data"]["filename"]):
        files = [confg_d["data"]["filename"]]
    elif glob.glob(confg_d["data"]["filename"]):
        files = sorted(glob.glob(confg_d["data"]["filename"]))
    elif isinstance(confg_d["data"]["filename"], list):
        files = confg_d["data"]["filename"]
    else:
        raise FileNotFoundError(f"Invalid filename(s) specified:\n{config_d['data']['filename']}")

    if not confg_d["data"].get("gridfile"):
        confg_d["data"]["gridfile"]=""

    for f in files:
        # Open specified file and load dataset
        dataset=load_dataset(f,confg_d["data"]["gridfile"])


        # Make the plots!
        plotit(confg_d,dataset,f)
