How to use Hydrabot
=====================
Start by setting up your hydrabot instance with this guide :ref:`setup`

You can use the bot by sending message in the choosen Discord Text Channel.
Command start with the prefix *!*

Available command(s)
-----------------------
Full command name with the short hande in parenthesis.


* !help (!h) : Get all available command with description.

* !position (!p) : Post all current positions.

  You can also view a specific token with ``!position TOKEN_SYMBOL``.

* !balance (!b) : Post all current tokens balance.

* !gas (!g) : Post current gas estimate for a Swap.

* !settings (!s) : Post current settings.
  
  You can edit them by posting ``!settings $SETTING_NAME $SETTING_VALUE``

* !wrap (!w) : To Wrap ETH to WETH
 
  This isn't tested on mainnet, use AT YOUR OWN RISK !


Getting started
-----------------
Make your first trade using the bot !

1. Start by reviewing the settings, set your default buy amount and confirm the slippage.

   * ``!settings`` to view all settings.
   * ``!settings buy AMOUNT`` to set it to your preferred value.
   * ``!settings slippage AMOUNT`` to set your slippage. Slippage is a percentage. 1 = 100%, 0.1 = 10%.


2. Track a Pair. Go to `Dexscreener <https://dexscreener.com>`_.

   *Be careful with the Pair you want to trade, inspect carefully the contract to no get scam !*

   * Copy the Pair address and paste it into the Text Channel.
   * The Bot should post the Pair information after.


3. Use the Pair Message Reaction to Trade.

   * Use the reaction to buy, sell and untrack the pair.


4. You can set a trading strategy on the Pair by replying to the Pair Message with the strategy name.

