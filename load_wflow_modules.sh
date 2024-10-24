
scrfunc_fp=$( readlink -f "${BASH_SOURCE[0]}" )
scrfunc_dir=$( dirname "${scrfunc_fp}" )

if [ -z "${1}" ]; then
  echo "You must provide the platform name as an argument"
else
  module use $scrfunc_dir/modulefiles
  module load wflow_$1 > /dev/null 2>&1

  conda activate mpas_app
fi
