import uxarray as ux
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

filename='history.2023-09-15_09.00.00.nc'

grid = ux.open_grid(filename)
print(grid)

uxds = ux.open_dataset(filename,filename)
print(uxds)

print(f"{uxds.uxgrid.sizes=}")
var = "vegfra"
print(f"{uxds[var]=}")

print(f"{uxds[var][:][0]=}")
#uxds["vegfra"][0].plot.rasterize(
#    title="Grid plot through uxgrid attribute",
#    backend="matplotlib",
#    aspect=2,
#    fig_size=500,
#)

pc = uxds[var][:][0].to_polycollection()

pc.set_antialiased(False)

pc.set_cmap("plasma")

fig, ax = plt.subplots(1, 1, figsize=(10, 5), constrained_layout=True)

ax.set_xlim((-180, 180))
ax.set_ylim((-90, 90))
ax.add_collection(pc)

plt.title("Poly Collection Plot")
plt.savefig('./MPAS_uxarray.png')
