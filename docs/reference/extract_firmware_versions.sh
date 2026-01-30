#!/bin/bash
# Extract latest stable (non-beta) firmware versions and dates from gpsinformation.net

# Function to get latest non-beta version and date for a device
get_firmware() {
    local url=$1
    local anchor=$2

    # Get the full line with version and date
    local line=$(curl -k -s "$url" | \
        sed -n "/<a name=\"$anchor\">/,/<\/table>/p" | \
        grep -v "Beta" | \
        grep "Ver\." | \
        head -1)

    # Extract version (e.g., 29.22)
    local version=$(echo "$line" | grep -oE "[0-9]+\.[0-9]+" | head -1)

    # Extract date (e.g., 11/04/2025)
    local date=$(echo "$line" | grep -oE "[0-9]{2}/[0-9]{2}/[0-9]{4}" | head -1)

    # Convert to FIT format (multiply by 100) and reformat date to YYYY-MM-DD
    if [ -n "$version" ] && [ -n "$date" ]; then
        local fit_version=$(echo "$version * 100" | bc | cut -d. -f1)
        local year=$(echo "$date" | cut -d/ -f3)
        local month=$(echo "$date" | cut -d/ -f1)
        local day=$(echo "$date" | cut -d/ -f2)
        echo "$fit_version,$year-$month-$day"
    fi
}

# Edge devices
echo "# Edge devices"
echo "Edge 1050 (4440): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge1050.htm' 'edge1050')"
echo "Edge 1040 (3843): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge1040.htm' 'edge1040')"
echo "Edge 840 (4062): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge840.htm' 'edge840')"
echo "Edge 830 (3122): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge830.htm' 'Edge830')"
echo "Edge 540 (4061): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge540.htm' 'edge540')"
echo "Edge 530 (3121): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge530.htm' 'Edge530')"
echo "Edge 550 (4633): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge550.htm' 'edge550')"
echo "Edge 850 (4634): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge850.htm' 'edge850')"
echo "Edge 1030 Plus (3570): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge1030.htm' 'edge1030_plus')"
echo "Edge 1030 (2713): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge1030.htm' 'edge1030')"
echo "Edge 520 Plus (3112): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge520.htm' 'edge520_plus')"
echo "Edge 520 (2067): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_edge520.htm' 'edge520')"
echo "Edge 130 Plus (3558): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_bike.htm' 'edge130_plus')"
echo "Edge 130 (2909): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_bike.htm' 'edge_130')"

echo ""
echo "# Fenix devices"
echo "Fenix 8 47mm (4536): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix8.htm' 'fenix8')"
echo "Fenix 8 Solar 51mm (4532): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix8.htm' 'fenix8_solar')"
echo "Fenix 8 Solar 47mm (4533): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix8.htm' 'fenix8_solar_large')"
echo "Fenix 8 43mm (4534): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix8.htm' 'fenix8_small')"
echo "Fenix 8 Pro (4631): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix8pro.htm' 'fenix8pro')"
echo "Fenix 7 (3906): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix7.htm' 'fenix7')"
echo "Fenix 7S (3905): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix7S.htm' 'fenix7S')"
echo "Fenix 7X (3907): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix7X.htm' 'fenix7X')"
echo "Fenix 7S Pro Solar (4374): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix7S.htm' 'fenix7S_pro_solar')"
echo "Fenix 7 Pro Solar (4375): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix7.htm' 'fenix7_pro_solar')"
echo "Fenix 7X Pro Solar (4376): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_fenix7X.htm' 'fenix7X_pro_solar')"
echo "Epix Gen 2 (3943): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_epix.htm' 'epix_2')"
echo "Epix Pro 42mm (4312): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_epix.htm' 'epix_gen2_pro_42')"
echo "Epix Pro 47mm (4313): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_epix.htm' 'epix_gen2_pro_47')"
echo "Epix Pro 51mm (4314): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_epix.htm' 'epix_gen2_pro_51')"

echo ""
echo "# Forerunner devices"
echo "Forerunner 965 (4315): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_965.htm' 'forerunner965')"
echo "Forerunner 955 (4024): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_955.htm' 'forerunner955')"
echo "Forerunner 265 Large (4257): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_265.htm' 'forerunner265')"
echo "Forerunner 265 Small (4258): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_265.htm' 'forerunner265_small')"
echo "Forerunner 255 (3992): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_255.htm' 'forerunner255')"
echo "Forerunner 255 Music (3990): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_255.htm' 'forerunner255_music')"
echo "Forerunner 255S (3993): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_255.htm' 'forerunner255_small')"
echo "Forerunner 255S Music (3991): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_255.htm' 'forerunner255_small_music')"
echo "Forerunner 945 (3113): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_forerunner_945.htm' 'forerunner945')"

echo ""
echo "# Tacx trainers"
echo "Tacx Training App Win (20533): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_tacx.htm' 'tacx_training_app_win')"
echo "Tacx Training App Mac (20534): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_tacx.htm' 'tacx_training_app_mac')"
echo "Tacx Training App Android (30045): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_tacx.htm' 'tacx_training_app_android')"
echo "Tacx Training App iOS (30046): $(get_firmware 'http://gpsinformation.net/allory/test/garfeat_tacx.htm' 'tacx_training_app_ios')"
