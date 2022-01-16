async function ethLogin() {
  const provider = new ethers.providers.Web3Provider(
      window.ethereum,
      "any"
  );
  const signer = await provider.getSigner();
  await provider.send("eth_requestAccounts", []);
  
  return signer
};


async function donate(amount) {
  var donation = amount;
  // console.log(donation.toString());
  const kbsI = new ethers.utils.Interface(readABI());
  const signer = await ethLogin();
  if (signer.provider.getNetwork() != '0x1'){
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: '0x1' }], // chainId must be in hexadecimal numbers. 0x00 = Mainnet
    });
    window.location.reload();
  } else {
    console.log("Good user, you are in mainnet!");
  }

  const contract = new ethers.Contract('0x9313F75F4C49a57D1D0158232C526e24Bb40f281', kbsI, signer);

  contract.functions.donate({value: ethers.utils.parseEther(donation.toString())}).then((tx) => {
    console.log(tx);
    displayDonationMSG("Thank you for your contribution to $UBI and Klerosboard!");
  }).catch((error) => {
    console.log('error!');
    // console.log(error);
    // console.log(error.throwError());
    displayDonationMSG("Error trying to perform the operation.");
  })
};

function displayDonationMSG(text) {
  var element = document.getElementById("donationResponse");
  console.log(element);
  element.innerHTML = text;
  return false;
}


async function login() {
  // post the data
  var signer = await ethLogin();
  address = await signer.getAddress();
  console.log("Logging with address: "+address);
  var ajax=$.ajax({
      type: "POST",
      data: JSON.stringify({'signer':address}),
      url: "https://klerosboard.com/_internalLogin",
      contentType: 'application/json;charset=UTF-8',

  }).done(function(){
      console.log('Logged in succesfully!')
      location.reload(); 
  });
  ajax.fail(function(data){
      console.log('error!');
      console.log(data);
  });
}

function readABI() {
  return [
    {
      "inputs": [
        { "internalType": "address", "name": "_ubiburner", "type": "address" },
        { "internalType": "uint8", "name": "_maintenanceFee", "type": "uint8" },
        {
          "internalType": "uint96",
          "name": "_donationPerMonth",
          "type": "uint96"
        }
      ],
      "stateMutability": "nonpayable",
      "type": "constructor"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "from",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "amount",
          "type": "uint256"
        }
      ],
      "name": "Donation",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "oldMaintainer",
          "type": "address"
        },
        {
          "indexed": true,
          "internalType": "address",
          "name": "newMaintainer",
          "type": "address"
        }
      ],
      "name": "MaintainerChanged",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "uint8",
          "name": "maintenanceFeeDivisor",
          "type": "uint8"
        }
      ],
      "name": "MaintenanceFeeChanged",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "previousOwner",
          "type": "address"
        },
        {
          "indexed": true,
          "internalType": "address",
          "name": "newOwner",
          "type": "address"
        }
      ],
      "name": "OwnershipTransferred",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": true,
          "internalType": "address",
          "name": "from",
          "type": "address"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "amount",
          "type": "uint256"
        }
      ],
      "name": "UBIBurnDonation",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "address",
          "name": "ubiburner",
          "type": "address"
        }
      ],
      "name": "UBUBurnerChanged",
      "type": "event"
    },
    {
      "anonymous": false,
      "inputs": [
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "oldDonationAmount",
          "type": "uint256"
        },
        {
          "indexed": false,
          "internalType": "uint256",
          "name": "donationAmount",
          "type": "uint256"
        }
      ],
      "name": "donationPerMonthChanged",
      "type": "event"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "_donationPerMonth",
          "type": "uint256"
        }
      ],
      "name": "changeDonationPerMonth",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        { "internalType": "address", "name": "_maintainer", "type": "address" }
      ],
      "name": "changeMaintainer",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [{ "internalType": "uint8", "name": "_newFee", "type": "uint8" }],
      "name": "changeMaintenanceFee",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        { "internalType": "address", "name": "_ubiburner", "type": "address" }
      ],
      "name": "changeUBIburner",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "donate",
      "outputs": [],
      "stateMutability": "payable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "donationPerMonth",
      "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [{ "internalType": "address", "name": "", "type": "address" }],
      "name": "getTotalDonor",
      "outputs": [{ "internalType": "uint256", "name": "", "type": "uint256" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [{ "internalType": "address", "name": "", "type": "address" }],
      "name": "isDonor",
      "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "maintainer",
      "outputs": [{ "internalType": "address", "name": "", "type": "address" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "maintenanceFeeDivisor",
      "outputs": [{ "internalType": "uint8", "name": "", "type": "uint8" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "owner",
      "outputs": [{ "internalType": "address", "name": "", "type": "address" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "renounceOwnership",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        { "internalType": "address", "name": "newOwner", "type": "address" }
      ],
      "name": "transferOwnership",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "ubiburner",
      "outputs": [{ "internalType": "address", "name": "", "type": "address" }],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "withdrawMaintenance",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    }
  ]
}