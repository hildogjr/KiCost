# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'
# Export .version.__version__ as a module version
from .version import __version__, __build__  # noqa: F401

# Definition used inside KiCost and its submodules, here for convenience
from .log__ import (debug, debug_detailed, is_debug_detailed, debug_overview,  is_debug_overview, debug_obsessive,  is_debug_obsessive,  # noqa F401
                    debug_full, debug_general, info, warning, error, get_logger, set_logger, DEBUG_OVERVIEW, DEBUG_DETAILED,
                    DEBUG_OBSESSIVE, DEBUG_HTTP_HEADERS, DEBUG_HTTP_RESPONSES, DEBUG_FULL)
from .global_vars import (SEPRTR, W_FLDOVR, ERR_INPUTFILE, W_DUPWRONG, ERR_FIELDS, W_INCQTY, W_REPMAN, W_MANQTY, W_NOINFO, ERR_SCRAPE,   # noqa: F401
                          W_APIFAIL, W_AMBIPN, W_ASSQTY, DEFAULT_CURRENCY, NO_PRICE, W_BADPRICE, BASE_OP_TYPES)

# Definitions exported to other applications using KiCost as a module
from .global_vars import KiCostError, DistData, PartGroup  # noqa F401
from .kicost import query_part_info, solve_parts_qtys  # noqa F401
from .config import load_config  # noqa F401
from .spreadsheet import create_worksheet, Spreadsheet  # noqa F401
from .__main__ import configure_kicost_apis, ProgressConsole, init_all_loggers  # noqa F401
from .distributors import get_distributors_list, get_dist_name_from_label, set_distributors_progress, is_valid_api  # noqa F401
