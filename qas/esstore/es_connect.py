from elasticsearch import Elasticsearch
import logging
from qas.esstore.es_config import __index_name__, __doc_type__, __wiki_title__, __wiki_updated_date__, __wiki_content__,\
    __wiki_content_info__, __wiki_content_table__, __wiki_revision__, __wiki_pageid__, __wiki_raw__, __num_shards__,\
    __num_replicas__, __analyzer_en__, __index_version__
"""
Meta Class for managing elasticsearch db connection. It also serves as an singleton
"""

logger = logging.getLogger(__name__)


class ElasticSearchMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(ElasticSearchMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ElasticSearchConn(metaclass=ElasticSearchMeta):
    __hostname__ = 'localhost'
    __port__ = 9200
    __es_conn__ = None
    es_index_config = None

    def __init__(self):
        es_host = {'host': self.__hostname__, 'port': self.__port__}
        self.__es_conn__ = Elasticsearch(hosts=[es_host])
        self.set_up_index()

    @staticmethod
    def get_index_mapping():
        return {
            "settings": {
                "number_of_shards": __num_shards__,
                "number_of_replicas": __num_replicas__
            },
            "mappings": {
                __doc_type__: {
                    "_meta": {
                        "version": 1
                    },
                    "properties": {
                        __wiki_title__: {
                            "type": "text",
                            "analyzer": __analyzer_en__
                        },
                        __wiki_updated_date__: {
                            "type": "date"
                        },
                        __wiki_raw__: {
                            "type": "object",
                            "enabled": "false"
                        },
                        __wiki_content__: {
                            "type": "text",
                            "analyzer": __analyzer_en__
                        },
                        __wiki_content_info__: {
                            "type": "text",
                            "analyzer": __analyzer_en__
                        },
                        __wiki_content_table__: {
                            "type": "text",
                            "analyzer": __analyzer_en__
                        },
                        __wiki_revision__: {
                            "type": "long"
                        }
                    }
                }
            }
        }

    def create_index(self):
        # ignore 400 cause by IndexAlreadyExistsException when creating an index
        self.es_index_config = ElasticSearchConn.get_index_mapping()
        res = self.__es_conn__.indices.create(index=__index_name__, body=self.es_index_config, ignore=400)
        if 'error' in res and res['status'] == 400:
            logger.debug("Index already exists")
        elif res['acknowledged'] and res['index'] == __index_name__:
            logger.debug("Index Created")
        else:
            logger.error("Index creation failed")

    def update_index(self, current_version):

        """
        Existing type and field mappings cannot be updated. Changing the mapping would mean invalidating already indexed documents.
        Instead, you should create a new index with the correct mappings and reindex your data into that index.
        """

        updated_mapping = None

        # Migrating from version 1 to version 2
        if current_version == 1 and __index_version__ == 2:
            updated_mapping = {
                "_meta": {
                        "version": __index_version__
                    },
                "properties": {
                    __wiki_content_info__: {
                        "type": "text",
                        "analyzer": __analyzer_en__
                    },
                    __wiki_content_table__: {
                        "type": "text",
                        "analyzer": __analyzer_en__
                    }
                }
            }

        if updated_mapping is not None:
            self.__es_conn__.indices.close(index=__index_name__)
            res = self.__es_conn__.indices.put_mapping(index=__index_name__, doc_type=__doc_type__, body=updated_mapping)
            self.__es_conn__.indices.open(index=__index_name__)

    def set_up_index(self):
        index_exists = self.__es_conn__.indices.exists(index=__index_name__)
        if not index_exists:
            self.create_index()
        else:
            res = self.__es_conn__.indices.get_mapping(index=__index_name__, doc_type=__doc_type__)
            current_version = res[__index_name__]['mappings'][__doc_type__]['_meta']['version']
            if current_version < __index_version__:
                self.update_index(current_version)

    def get_db_connection(self):
        return self.__es_conn__
