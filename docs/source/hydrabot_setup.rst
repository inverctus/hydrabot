Hydrabot setup
===============
 Follow this guide to run your own hydrabot instance


Software Requirement(s)
---------------------------

* Git (https://git-scm.com/)
* Docker with compose plugin (https://docs.docker.com/get-docker/)

.. _setup:

Setup
----------------

1. Create an ethereum wallet. You will need the private key.

2. Hydrabot depends on other service to works;
  
  * BaseScan API Key
  
    Used to fetch smart contract ABI.

    1. Create an account on https://basescan.org/.
    2. Login and click on your username and a dropdown menu should appear, click on API Keys.
    3. Click on Add Button, choose a name for the API Key.
    4. Keep the api key close. We will need it soon.
    
  * Web3 Node URL
     
    Used to call and send transaction on ethereum network.

    1. Create an account on  https://alchemy.com/.
    2. Login and go in your dashboard.
    3. Create a new app;
        * Chain: Base
        * Network: Ethereum
    4. Copy the HTTPS url from API Key modal.
    5. Keep that url close. We will need it soon.
    
  * Discord Bot Token
    
    Used as a front end to send buy & sell signal and also post periodic update on current position.

    1. Create a discord server for your bot.
    2. Go to https://discord.com/developers/applications
    3. Create a new application; choose a name and click on create.
    4. Under Settings menu, click on Bot.
    5. Under Privileged Gateway Intents, toggle Message Content Intent on.
    6. Connect the bot to your server
        1. Under Settings menu, click on OAuth2.
        2. Go to OAuth2 URL Generator section.
        3. Select thoses scopes: bot.
        4. Under bot permissions, select: Send Messages, Embed Links, Add Reaction, Read Message/View Channels.
        5. Copy the generated url and go to that url with your browser.
        6. This will connect the bot to your discord server.
        7. Select your server and authorize.
        8. Under Settings menu, click on Bot.
        9. Click on the Reset Token button.
        10. Copy the token and keep it close, we will need it soon.
    7. Create a new text channel in your server, right-click on it and copy the channel id.
    8. Click on your discord user tag and copy your user id.
    
3. Clone the repository and go open a shell in that folder.

   On windows, we recommend to use Git bash.

4. Build the docker images.

   You can do this by running the **build_image.sh** script.
 
.. code-block:: console

    $ ./build_images.sh


5. Copy the **vars.example.sh** and rename it to **vars.sh**.

  * Open **vars.sh** with your favorite text editor
  * Fill the variable(s);

.. code-block:: console

    export DB_PASSWORD=Generate a password for the database
    export BOT_TOKEN=Discord bot token
    export WALLET_PRIVATE_KEY=Your Ethereum wallet private key
    export WEB3_PROVIDER_URL=Alchemy web3 https url
    export LISTEN_CHANNEL_ID=Discord Text Channel Id
    export BASESCAN_API_KEY=Basescan Api Key
    export USER_IDS=Your discord user id

6. You are now running the start the bot.
  
  * Start the bot with **start.sh** script and you can stop it with **stop.sh**.

.. code-block:: console

    $ ./start.sh

.. code-block:: console

    $ ./stop.sh

7. You can now try to trade !