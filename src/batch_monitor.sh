parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
echo "$parent_path"
basedir=$1
for file in "$basedir"/*; do
    if [[ -f "$file" && ($file == *mi2log || $file == *qmdl) ]] ; then
    	base_name=$(basename $file)
    	output="mobility_${base_name}.txt"
        echo "$output"
    	if [ ! -f "$output" ]; then
            echo "python ${parent_path}/offline_mobility_monitor.py ${file} > ${output}"
    		python "${parent_path}/offline_mobility_monitor.py" "$file" > "$output"
    	fi
    fi
done