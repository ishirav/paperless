import itertools
import os
import re
import subprocess
from google.cloud import vision
from django.conf import settings
from documents.parsers import DocumentParser, ParseError


class OCRError(Exception):
    pass


class GoogleOcrDocumentParser(DocumentParser):
    """
    This parser uses Google Cloud Vision to try and get some text out of a rasterised
    image, whether it's a PDF, or other graphical format (JPEG, TIFF, etc.)
    """

    CONVERT = settings.CONVERT_BINARY
    DENSITY = settings.CONVERT_DENSITY if settings.CONVERT_DENSITY else 300
    THREADS = int(settings.OCR_THREADS) if settings.OCR_THREADS else None
    UNPAPER = settings.UNPAPER_BINARY
    DEFAULT_OCR_LANGUAGE = settings.OCR_LANGUAGE

    def get_thumbnail(self):
        """
        The thumbnail of a PDF is just a 500px wide image of the first page.
        """

        run_convert(
            self.CONVERT,
            "-scale", "500x5000",
            "-alpha", "remove",
            self.document_path + '[0]', os.path.join(self.tempdir, "thumbnail.jpg")
        )

        return os.path.join(self.tempdir, "thumbnail.jpg")

    def get_text(self):

        images = self._get_images()

        try:

            return self._ocr(images)
        except OCRError as e:
            raise ParseError(e)

    def _get_images(self):
        """
        Convert the document to one image per page
        """

        # Convert PDF to multiple images
        output_format = 'jpg'
        img = os.path.join(self.tempdir, "convert-%04d." + output_format)
        run_convert(
            self.CONVERT,
            "-density", str(self.DENSITY),
            "-depth", "8",
            "-alpha", "Off",
            self.document_path, img,
        )

        # Get a list of converted images
        imgs = []
        for f in os.listdir(self.tempdir):
            if f.startswith('convert') and f.endswith(output_format):
                imgs.append(os.path.join(self.tempdir, f))

        return sorted(filter(lambda __: os.path.isfile(__), imgs))

    def _ocr(self, imgs):
        """
        Performs OCR on the images.
        """

        client = vision.ImageAnnotatorClient()

        texts = []

        for index, img in enumerate(imgs):
            self.log("info", "Running OCR on %s" % img)
            with open(img, 'rb') as f:
                content = f.read()
            if index == 0:
                # Try to detect a logos on the first page
                try:
                    response = client.logo_detection({'content': content})
                    for logo in response.logo_annotations:
                        texts.append('<' + logo.description + '>')
                except:
                    pass
            else:
                # Add a page number
                texts.append('===== %d =====' % (index + 1))
            # Detect full text
            response = client.document_text_detection({'content': content})
            texts.append(response.full_text_annotation.text.replace('\\n', '\n'))

        return '\n'.join(texts)


def run_convert(*args):

    environment = os.environ.copy()
    if settings.CONVERT_MEMORY_LIMIT:
        environment["MAGICK_MEMORY_LIMIT"] = settings.CONVERT_MEMORY_LIMIT
    if settings.CONVERT_TMPDIR:
        environment["MAGICK_TMPDIR"] = settings.CONVERT_TMPDIR

    subprocess.Popen(args, env=environment).wait()


