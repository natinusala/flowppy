#Ajout de opdis dans le PATH
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
export PATH=$DIR/opdis/dist:$PATH

#Exécution
python3.4 src/main.py