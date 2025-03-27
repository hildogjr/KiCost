==================
Configuration file
==================

The configuration is read from `~/.config/kicost/config.yaml`. Where `~` is the user's directory.

You can specify the name of the configuration file from the command line using `-c` or `--config` options.

Currently the main purpose of this file is to configure the distributors APIs.

The format is YAML and here is an example: ::

    # KiCost configuration file
    kicost:
      version: 1
      # Cache Time To Live in days, -1 is forever
      # Default is 7
      cache_ttl: -1
      # Base directory for the APIs caches
      # cache_path: ~/.cache/kicost
    
    
    APIs:
      Digi-Key:
        # Digi-Key Client ID for a registered APP
        # client_id: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        # Digi-Key Client Secret for a registered APP
        # client_secret: XXXXXXXXXXXXXXXX
        # Version of the Digi-Key API, use 4 unless you have old credentials for the V3 API
        # version: 4
        # Use the sandbox server, doesn't count the usage, but returns old data
        # sandbox: false
        # Only enabled if the client_id and client_secret are defined
        # enable: true
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Digi-Key
        # Exclude products offered by 3rd party associates (marketplace)
        # exclude_market_place_products: false
      Element14:
        # Element14 includes: Farnell, Newark and CPC
        # Element14 Product Search API key
        # key: XXXXXXXXXXXXXXXXXXXXXXXX
        # Only enabled if the key is defined
        # enable: false
        # Country used for Farnell queries.
        # Supported countries: BG,CZ,DK,AT,CH,DE,IE,IL,UK,ES,EE,FI,FR,HU,IT,LT,
        # LV,BE,NL,NO,PL,PT,RO,RU,SK,SI,SE,TR,CN,AU,NZ,HK,SG,MY,PH,TH,IN,KR,VN
        # farnell_country: UK
        # Country used for Newark queries.
        # Supported countries: US,CA,MX
        # newark_country: US
        # Country used for CPC queries.
        # Supported countries: UK,IE
        # cpc_country: UK
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Element14
      Mouser:
        # Mouser Part API key
        # key: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        # Only enabled if the key is defined
        # enable: false
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Mouser
      Nexar:
        # Nexar client ID
        # client_id: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        # Nexar client secret
        # client_secret: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        # Only enabled if the client_id and client_secret are defined
        # enable: false
        # Country where we are buying
        # country: US
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Nexar

Data from the APIs is cached `cache_ttl` days, using -1 means to keep them cached forever.
Using 0 will force to do all searches again (no cache).

You don't need to specify the `cache_path` for each API, they are derived from the main option.
The default value for the main cache path is `~/.cache/kicost`.

Currently all the APIs needs some kind of key/token, lamentably we no longer have an API that doesn't need it.

The `Nexar` API provides access to various distributors. It has a free option, with a current limit of 1000 parts/month.
This is free and you just need to register yourself and an application at Nexar_.

The other APIs are provided by each distributor, and they usually offer a free service with a generous limit.

Note that the keys needed are the ones provided by the distributor to use its API, they aren't your user name
and password for the site. As an example, to get the keys for Digi-Key you'll need to visit the API_site_.
Then you have to register and get a `clientId` and a `clientSecret` to use in the configuration file.

The current Digi-Key plugin needs to validate the user using a complex mechanism. It will open a navigator
window to get a token. If you get an error about a wrong certificate please ignore it. The obtained token
is cached, so you don't need to validate it all the time.

You can also define options using environment variables. As an example, you can specify Mouser's key defining
the `MOUSER_KEY` environment variable. Note that environment variables has more precedence than the default config file.
But command line options, including any configuration file passed using it, has the highest priority.

.. _API_site: https://developer.digikey.com/get_started
.. _Nexar: https://nexar.com/api
