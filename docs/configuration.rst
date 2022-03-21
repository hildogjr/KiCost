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
        # Use the sandbox server, doesn't count the usage, but returns old data
        # sandbox: false
        # Only enabled if the client_id and client_secret are defined
        # enable: true
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Digi-Key
      Mouser:
        # Mouser Part API key
        # key: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        # Only enabled if the key is defined
        # enable: false
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Mouser
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
      Octopart:
        # Octopart API Key
        # key: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # API level: 3 or 4
        # level: 4
        # The extended API is for the Pro plan
        # extended: false
        # Only enabled if the key is defined
        # enable: false
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/Octopart
      KitSpace:
        # Normally enabled
        # enable: true
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/KitSpace
      TME:
        # TME token (anonymous or private)
        # token: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        # TME application secret
        # app_secret: XXXXXXXXXXXXXXXXXXXX
        # Only enabled if the token and app_secret are defined
        # enable: false
        # Country where we are buying
        # country: US
        # Language for the texts
        # language: EN
        # Directory for the APIs caches
        # cache_path: ~/.cache/kicost/TME

Data from the APIs is cached `cache_ttl` days, using -1 means to keep them cached forever.
Using 0 will force to do all searches again (no cache).

You don't need to specify the `cache_path` for each API, they are derived from the main option.
The default value for the main cache path is `~/.cache/kicost`.

The `KitSpace` API is the only API that doesn't need a key to be used.
This is a service kindly provided by the KitSpace_ project.
As such, is a limited resource. So you should consider getting keys for the distributors you use.

The `Octopart` API provides access to various distributors. It has a free option, with strong limits.
Note that you need to provide a valid credit card in order to get a free key.

The other APIs are provided by each distributor, and they usually offer a free service with a generous limit.

.. _KitSpace: https://kitspace.org/
