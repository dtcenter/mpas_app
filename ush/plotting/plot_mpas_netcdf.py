#!/usr/bin/env python3
"""
Script for plotting MPAS input and/or output in native NetCDF format"
"""
import argparse
import logging
import sys

import uxarray as ux
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from uwtools.api.config import get_yaml_config


def plotit(config_d: dict,log: logging.Logger) -> None:
    """
    The main program that makes the plot(s)
    """
    print(config_d)
    fn=config_d["files"]["filename"]
    grid = ux.open_grid(fn)
    log.debug(grid)

    uxds = ux.open_dataset(fn,fn)

    for var in uxds:
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
    
        try:
            pc = sliced.to_polycollection()
        except:
            log.info(f"Could not convert {var} to polycollection; there may be additional dimensions here")
            continue
    
        pc.set_antialiased(False)
    
        pc.set_cmap("plasma")
    
        fig, ax = plt.subplots(1, 1, figsize=(10, 5), constrained_layout=True)
    

        ax.set_xlim((config_d["plot"]["lonrange"][0],config_d["plot"]["lonrange"][1]))
        ax.set_ylim((config_d["plot"]["latrange"][0],config_d["plot"]["latrange"][1]))
    
        # add geographic features
    #    ax.add_feature(cfeature.COASTLINE)
    #    ax.add_feature(cfeature.BORDERS)
    
        ax.add_collection(pc)
    
        plt.title(f"{var} Plot")
        plt.savefig(f'images/MPAS_{var}.png')
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
    confg_d = get_yaml_config(config=args.config)
    plotit(confg_d,log)
