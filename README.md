# KlerosJurorsDashboard
This page lets you know your chances to be drawn as a Juror in a Kleros Court. It also shows you the evolution of cases, along with history of the Courts.

You can visit the dashboard in [klerosboard.com](klerosboard.com)

Please open an issue if you found any, or improvements feedbacks.

This Dashboard was inspired by the Kleroscan tool developed by Marc Zeller, visit his repo in [github](https://github.com/marczeller/Kleros-Monitor-Bot).

I would like to thank all the Kleros team for the support in the development, specially to William George who helps me with the mathematics.

For more information about Kleros visit [kleros.io](kleros.io)

# Local Deployment
To deploy klerosboard locally you need to follow the next steps:

0) Clone the repository
```
# Use HTTPS
git clone https://github.com/salgozino/KlerosJurorDashboard.git

# Or use SSH
git clone git@github.com:salgozino/KlerosJurorDashboard.git
```

1) Create a virtualenv and pip install all the requirements
```
# Install virtualenv
pip3 install virtualenv

# Create virtual environment 
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# In the virtual environment download dependencies
python -m pip install -r requirements.txt
```

2) Create the following environment variables:
# TODO: I HAVE NO CLUE HOW TO DO THIS

``` 

 * INFURA_NODE=[your_infura_node]
 * FLASK_APP=application
```

3) Launch app by running flask
``` 
flask run
```
