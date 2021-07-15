# KlerosJurorsDashboard
This page lets you know your chances to be drawn as a Juror in a Kleros Court. It also shows you the evolution of cases, along with history of the Courts.

You can visit the dashboard in klerosboard.com

Please open an issue if you found any, or improvements feedbacks.

This Dashboard was inspired by the Kleroscan tool developed by Marc Zeller, visit his repo in [github](https://github.com/marczeller/Kleros-Monitor-Bot).

I would like to thank all the Kleros team for the support in the development, specially to William George who helps me with the mathematics.

For more information about Kleros visit [kleros.io](kleros.io)

# Local Deployment
To deploy klerosboard locally you need to follow the next steps:
0) Clone de repo
1) Create a virtualenv and pip install all the requirements
2) Create the following enviromental variables:
 * SUBGRAPH_ID=[check node ID in https://thegraph.com/legacy-explorer/subgraph/salgozino/klerosboard for mainnet]
 * SUBGRAPH_ID_XDAI=[check node ID in https://thegraph.com/legacy-explorer/subgraph/salgozino/klerosboard for xDai]
 * INFURA_NODE=[your_infura_node]
 * FLASK_APP=application
3) flask run