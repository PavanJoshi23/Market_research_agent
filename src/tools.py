import os

from langchain_community.utilities import SearxSearchWrapper

search = SearxSearchWrapper(searx_host=os.environ["SEARXNG_HOST"])
