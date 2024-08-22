import sys

import uxarray as ux
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

filename='history.2023-09-15_09.00.00.nc'

grid = ux.open_grid(filename)
print(grid)

uxds = ux.open_dataset(filename,filename)

for var in uxds:
    if "n_face" not in uxds[var].dims:
        print(f"Variable {var} not face-centered, skipping")
        continue
    print(f"Plotting variable {var}")
    sliced=uxds[var]
    if "Time" in sliced.dims:
        print("Plotting first time step")
        sliced=sliced.isel(Time=0)
    if "nVertLevels" in sliced.dims:
        print("Plotting first vertical level")
        sliced=sliced.isel(nVertLevels=0)

    print(sliced)

#uxds["vegfra"][0].plot.rasterize(
#    title="Grid plot through uxgrid attribute",
#    backend="matplotlib",
#    aspect=2,
#    fig_size=500,
#)

    try:
        pc = sliced.to_polycollection()
    except:
        print(f"Could not convert {var} to polycollection; there may be additional dimensions here")
        continue

    pc.set_antialiased(False)

    pc.set_cmap("plasma")

    fig, ax = plt.subplots(1, 1, figsize=(10, 5), constrained_layout=True)

    ax.set_xlim((-130, -60))
    ax.set_ylim((20, 50))

    # add geographic features
#    ax.add_feature(cfeature.COASTLINE)
#    ax.add_feature(cfeature.BORDERS)

    ax.add_collection(pc)

    plt.title(f"{var} Plot")
    plt.savefig(f'./MPAS_{var}.png')
    plt.close()
