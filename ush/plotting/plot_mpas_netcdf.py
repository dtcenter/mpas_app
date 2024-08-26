#!/usr/bin/env python3
"""
Script for plotting MPAS input and/or output in native NetCDF format"
"""
import argparse
import copy
import logging
import sys

import uxarray as ux
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

import uwtools.api.config as uwconfig

def load_dataset(config_d: dict) -> ux.UxDataset:
    """
    Program loads the dataset from the specified MPAS NetCDF file
    and returns it as a ux.UxDataset object
    """

    fn=config_d["data"]["filename"]
    grid = ux.open_grid(fn)
    logging.debug(grid)

    return ux.open_dataset(fn,fn)

def plotit(config_d: dict,uxds: ux.UxDataset) -> None:
    """
    The main program that makes the plot(s)
    """
    fn=config_d["data"]["filename"]
    grid = ux.open_grid(fn)
    logging.debug(grid)

    uxds = ux.open_dataset(fn,fn)


    # To plot all variables, call plotit() recursively, trapping errors
    if config_d["data"]["var"]=="all":
        newconf = copy.deepcopy(config_d)
        for var in uxds:
            logging.debug(f"Trying to plot variable {var}")
            newconf["data"]["var"]=[var]
            try:
                plotit(newconf,uxds)
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
                plotit(newconf,uxds)
            except Exception as e:
                logging.warning(f"Could not plot variable {newconf['data']['var']}, level {lev}")
                logging.warning(e)

    elif isinstance(config_d["data"]["var"], list):
        for var in config_d["data"]["var"]:
            if "n_face" not in uxds[var].dims:
                logging.info(f"Variable {var} not face-centered, skipping")
                continue
            logging.info(f"Plotting variable {var}")
            sliced=uxds[var]
            if "Time" in sliced.dims:
                logging.info("Plotting first time step")
                sliced=sliced.isel(Time=0)
            if "nVertLevels" in sliced.dims:
                if config_d["data"]["lev"]:
                    lev=config_d["data"]["lev"][0]
                else:
                    lev=0
                logging.debug(f'Plotting vertical level {lev}')
                sliced=sliced.isel(nVertLevels=lev)

            # Set some special variables that can be used in plot titles, etc.
            units=uxds[var].attrs["units"]
            varln=uxds[var].attrs["long_name"]


            logging.debug(sliced)
            pc=sliced.to_polycollection()

            pc.set_antialiased(False)
    
            pc.set_cmap(config_d["plot"]["colormap"])
    
            fig, ax = plt.subplots(1, 1, figsize=(config_d["plot"]["figwidth"], config_d["plot"]["figheight"]),
                                   dpi=config_d["plot"]["dpi"], constrained_layout=True)
    
    
            ax.set_xlim((config_d["plot"]["lonrange"][0],config_d["plot"]["lonrange"][1]))
            ax.set_ylim((config_d["plot"]["latrange"][0],config_d["plot"]["latrange"][1]))
    
            # add geographic features
        #    ax.add_feature(cfeature.COASTLINE)
        #    ax.add_feature(cfeature.BORDERS)
    
            coll = ax.add_collection(pc)    

            plottitle=config_d["plot"]["title"].format(var=var,lev=lev,units=units,varln=varln)
            plt.title(plottitle)
            plt.colorbar(coll,ax=ax,orientation='horizontal')
            outfile=config_d["plot"]["filename"].format(var=var,lev=lev)
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

    # Open specified file and load dataset
    dataset=load_dataset(confg_d)

    # Make the plots!
    plotit(confg_d,dataset)
