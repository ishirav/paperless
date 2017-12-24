import re

from .parsers import GoogleOcrDocumentParser
from django.conf import settings


class ConsumerDeclaration(object):

    MATCHING_FILES = re.compile("^.*\.(pdf|jpe?g|gif|png|tiff?|pnm|bmp)$")

    @classmethod
    def handle(cls, sender, **kwargs):
        return cls.test

    @classmethod
    def test(cls, doc):

        if settings.GOOGLE_APPLICATION_CREDENTIALS and cls.MATCHING_FILES.match(doc.lower()):
            return {
                "parser": GoogleOcrDocumentParser,
                "weight": 1 # must be higher than the tesseract parser's weight
            }

        return None
