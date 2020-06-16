cd /app_lib

git clone https://github.com/simonsobs/sotoddb.git
git clone https://github.com/simonsobs/sotodlib.git

# Installs sotoddb. Will take this out when it's no longer needed
cd sotoddb
echo "Installing sotoddb..."
pip3 install .

cd /app_lib/sotodlib
echo "Installing sotodlib..."
git checkout tags/v0.3.0
pip3 install -e .
