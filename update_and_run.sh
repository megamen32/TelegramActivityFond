unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=ubuntu;;
    Darwin*)    machine=mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac

git config pull.rebase false
date=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p backups
zip -r backups/${date}.zip data/
${machine}_venv/bin/python main.py
