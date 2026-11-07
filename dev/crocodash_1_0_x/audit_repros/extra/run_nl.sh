source /glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/audit/env.sh
G=/glade/derecho/scratch/manishrv/tmp/claude-44953/-glade-u-home-manishrv-documents-croc/8dbab665-7998-4a92-b4e6-579de0e188a7/scratchpad/gap2
cd $G; HOME=$G/fakehome timeout 1800 $PY nonlocal.py $G $1 $2 > nl_$1_$2.log 2>&1; echo "EXIT $?" >> nl_$1_$2.log
