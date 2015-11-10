# -*- coding: utf-8 -*-

#Import des modules
import sys;
from clize import Parameter, run;
import shutil;
from sigtools.modifiers import annotate, autokwoargs;
import tempfile;
import os.path;
import OutputManager;
import subprocess;
from xml.dom.minidom import parseString;
import traceback;
import networkx as nx;

#Import des données
import Instruction;
import Operand;

#Import des drivers
import GraphDriver;
import RegularDriver;
import CondensedDriver;

#Liste des valeurs supportées par les différentes options
render_engines = ["dot", "neato", "circo", "fdp", "sfdp", "twopi"];
output_types = ["png", "gif", "svg", "svgz", "dot"];

#Main
@annotate(input_file = "i", output_file = "o", render_engine = "r", graph_type = "t", quiet_mode = "q")
@autokwoargs
def main(input_file = "", output_file = "", render_engine = "dot", graph_type = "regular", quiet_mode = False, *render_options):
    """
    Creates an control flow graph from a binary file using opdis and graphviz.
    
    input_file: The binary file to create the graph from. Will use stdin if missing.
    
    output_file: The file to save the graph to (can be .png, .gif, .svg, .svgz, .dot). Will use stdout with PNG format if missing.
    
    render_engine: The graphviz engine to use when rendering the graph. Can be "dot", "neato", "circo", "fdp", "sfdp" or "twopi".
    
    graph_type: The type of the final graph. Can be "regular" (one instruction per node) or "condensed" (multiple instructions per node, jumps and calls as edges).
    
    render_options: The options to use when rendering the graph. See graphviz's "dot" manual for more details.
    
    quiet_mode: If enabled, the program will not output anything except for the resulting graph, even when failing.
    """
        
    #Création de l'OutputManager qui gère la sortie standard (erreurs, données)
    outputManager = OutputManager.OutputManager(quiet_mode);
    
    #Vérification de la présence d'opdis dans le PATH
    if (shutil.which("opdis") is None):
        outputManager.print_error("Unable to find opdis, is it installed ?");
        return;
        
    #TODO Vérifier la présence de graphviz
    
    #Chargement des drivers
    graph_drivers = {};
    for sub in GraphDriver.GraphDriver.__subclasses__():
        driver = sub(outputManager);
        graph_drivers[driver.get_name()] = driver;
        
    #Vérification de la validité des options
    #render_engine
    if not render_engine in render_engines:
        outputManager.print_message("Unknown render engine : " + render_engine);
        return;
    #graph_type
    if not graph_type in graph_drivers:
        outputManager.print_message("Unknown graph type : " + graph_type);
        return;
    #input_file - si l'option est présente le fichier doit exister
    if input_file and not os.path.isfile(input_file):
        outputManager.print_message("File not found : " + input_file);
        return;
    #output_file - doit être un format reconnu
    output_file_format = "";
    if output_file:
        output_file_array = output_file.split(".");
        if (len(output_file_array) == 1):
            outputManager.print_message("Missing output file extension.");
            return;
        output_file_format = output_file_array[len(output_file_array)-1];
        if not output_file_format in output_types:
            outputManager.print_message("Unsupported output format : " + output_file_format);
            return;
        
    #Lecture des données en entrée
    if not input_file:
        #Fichier en entrée non présent, lecture depuis l'entrée standard
        binary = sys.stdin.read();
        
        #On écrit ce qu'on a en entrée standard dans un fichier temporaire pour opdis
        binary_file = tempfile.NamedTemporaryFile(delete = False);
        binary_file.write(bytes(binary, 'UTF-8'));
        binary_file.close();
        input_file = binary_file.name;
        
    #Traitement
    try:
        #Exécution d'opdis et récupération du XML
        xml = subprocess.Popen(["opdis", "-f", "xml", "-E", input_file], stdout=subprocess.PIPE).stdout.read();
        document = parseString(xml).documentElement;   
        
        #Création de la liste des instructions
        instructions_table = [];
        vma_instructions_table = {};
        
        for instructionNode in document.getElementsByTagName("instruction"):
            instruction = Instruction.Instruction(
                get_xml_child_value(instructionNode, "offset"),
                get_xml_child_value(instructionNode, "vma"),
                get_xml_child_value(instructionNode, "ascii"),
                get_xml_child_value(instructionNode, "mnemonic")
            );
            
            if (xml_node_has_child(instructionNode, "operands")):
                for operandNode in instructionNode.getElementsByTagName("operand"):
                    operand = Operand.Operand(
                        operandNode.attributes["name"],
                        get_xml_child_value(operandNode, "ascii")
                    );
                    instruction.add_operand(operand);
                    
            instructions_table.append(instruction);
            vma_instructions_table[int(instruction.vma, 0)] = instruction;
                
        #Création du graphe
        graph = graph_drivers[graph_type].create_graph(instructions_table, vma_instructions_table);
        
        #Création du .dot dans un fichier temporaire
        dot_file = tempfile.NamedTemporaryFile(delete = False);
        nx.write_dot(graph, dot_file.name);
        
        #On regarde l'output demandé
        if output_file:
            #On veut un fichier
            makedirs(output_file);
            delete_file_if_exists(output_file);
            if output_file_format == "dot":
                #On copie le .dot temporaire là où il veut
                shutil.copyfile(dot_file.name, output_file);
            else:
                #On convertit l'image là où il veut
                output = render_graph(render_engine, output_file_format, dot_file.name);
                image = open(output_file, 'wb');
                image.write(output);
                image.close();
            outputManager.print_message("Graph saved to " + output_file);
        else:
            #On veut dans stdout
            #On convertit le .dot temporaire dans stdout
            pass;
        
        
    except Exception as e:
        outputManager.print_message("Error while creating graph : " + str(e) + "\n" + str(traceback.format_exc()));

#Méthode qui exécute le moteur de rendu et renvoie le fichier généré
def render_graph(render_engine, output_format, dot_file):
    return subprocess.Popen([render_engine, "-Gstart=42", "-Goverlap=false", "-Gsplines=true", "-Nshape=box", "-T" + output_format, dot_file], stderr=subprocess.DEVNULL, stdout=subprocess.PIPE).stdout.read();

#Méthode pour créer tous les dossiers parents d'un fichier
def makedirs(filename):
    if not os.path.exists(os.path.dirname(os.path.abspath(filename))):
        os.makedirs(os.path.dirname(os.path.abspath(filename)));
        
#Méthode pour supprimer un fichier qui existe peut-être
def delete_file_if_exists(filename):
    try:
        os.remove(filename)
    except OSError:
        pass;
        
#Méthode pour récupérer l'enfant d'un node XML
def get_xml_child_value(node, child_name):
    return node.getElementsByTagName(child_name)[0].childNodes[0].data;
    
def xml_node_has_child(node, child_name):
    return len(node.getElementsByTagName(child_name)) > 0;
        
if __name__ == "__main__":
    sys.argv[0] = "opdis-control-flow-graph";
    run(main);
