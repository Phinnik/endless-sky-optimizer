BASE_URL=https://raw.githubusercontent.com/endless-sky/endless-sky/refs/heads/master/data/human/
DATA_DIR=data/raw

wget $BASE_URL/ships.txt -P $DATA_DIR
wget $BASE_URL/weapons.txt -P $DATA_DIR
wget $BASE_URL/power.txt -P $DATA_DIR
wget $BASE_URL/outfits.txt -P $DATA_DIR
wget $BASE_URL/engines.txt -P $DATA_DIR
