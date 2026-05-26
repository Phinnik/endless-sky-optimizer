BASE_URL=https://raw.githubusercontent.com/endless-sky/endless-sky/refs/heads/master/data/human/
DATA_DIR=data/raw

mkdir -p $DATA_DIR

curl -sL "$BASE_URL/ships.txt" -o "$DATA_DIR/ships.txt"
curl -sL "$BASE_URL/weapons.txt" -o "$DATA_DIR/weapons.txt"
curl -sL "$BASE_URL/power.txt" -o "$DATA_DIR/power.txt"
curl -sL "$BASE_URL/outfits.txt" -o "$DATA_DIR/outfits.txt"
curl -sL "$BASE_URL/engines.txt" -o "$DATA_DIR/engines.txt"
