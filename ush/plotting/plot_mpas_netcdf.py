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

def load_dataset(config_d: dict,log: logging.Logger) -> ux.UxDataset:
    """
    Program loads the dataset from the specified MPAS NetCDF file
    and returns it as a ux.UxDataset object
    """

    fn=config_d["data"]["filename"]
    grid = ux.open_grid(fn)
    log.debug(grid)

    return ux.open_dataset(fn,fn)

def plotit(config_d: dict,uxds: ux.UxDataset,log: logging.Logger) -> None:
    """
    The main program that makes the plot(s)
    """
    fn=config_d["data"]["filename"]
    grid = ux.open_grid(fn)
    log.debug(grid)

    uxds = ux.open_dataset(fn,fn)

    # Each figure we will plot is a "polycollection"; we will first make a list of
    # all the polycollections we want to plot, then plot each one in a later loop
    pcs = []

    # Make sure the variable we want is present
    if config_d["data"]["var"]=="all":
        newconf = copy.deepcopy(config_d)
        for var in uxds:
            # To plot all variables, call plotit() recursively, trapping errors
            log.info(f"Trying to plot variable {var}")
            newconf["data"]["var"]=[var]
            try:
                plotit(newconf,uxds,log)
            except Exception as e:
                log.warning(e)
        
    elif isinstance(config_d["data"]["var"], list):
        for var in config_d["data"]["var"]:
            if "n_face" not in uxds[var].dims:
                log.info(f"Variable {var} not face-centered, skipping")
                continue
            log.info(f"Plotting variable {var}")
            sliced=uxds[var]
            if "Time" in sliced.dims:
                log.info("Plotting first time step")
                sliced=sliced.isel(Time=0)
            if "nVertLevels" in sliced.dims:
                log.info("Plotting first vertical level")
                sliced=sliced.isel(nVertLevels=0)

            log.debug(sliced)
            pcs.append(sliced.to_polycollection())
    else:
        raise ValueError('Config value data:var must either be a list of variable names or the literal string "all"')
 
    for pc in pcs:
        pc.set_antialiased(False)
    
        pc.set_cmap(config_d["plot"]["colormap"])
    
        fig, ax = plt.subplots(1, 1, figsize=(config_d["plot"]["figwidth"], config_d["plot"]["figheight"]),
                               dpi=config_d["plot"]["dpi"], constrained_layout=True)
    

        ax.set_xlim((config_d["data"]["lonrange"][0],config_d["data"]["lonrange"][1]))
        ax.set_ylim((config_d["data"]["latrange"][0],config_d["data"]["latrange"][1]))
    
        # add geographic features
    #    ax.add_feature(cfeature.COASTLINE)
    #    ax.add_feature(cfeature.BORDERS)
    
        ax.add_collection(pc)
    
        plt.title(f"{var} Plot")
        outfile=config_d["plot"]["filename"].format(var=var,lev=0)
        plt.savefig(outfile)
        plt.close()

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


def setup_config(config: str,log: logging.Logger) -> dict:
    log.debug(f"Reading options file {config}")
    config_d = uwconfig.get_yaml_config(config=config)
    log.debug(f"Expanding references to other variables and Jinja templates")
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

    log=setup_logging(logfile="log.plot", debug=args.debug)
    # Load settings from config file
    confg_d=setup_config(args.config,log)

    # Open specified file and load dataset
    dataset=load_dataset(confg_d,log)

    # Make the plots!
    plotit(confg_d,dataset,log)
