from azure.storage.blob import BlockBlobService
import pymongo as py
import os
import io
from PIL import Image
import wand.image as wd


_url = os.environ['VISION_API']
_key = os.environ['VISION_KEY']
_maxNumRetries = 10

def create_jpg(f):
    """Create multipage JPG from PDF.

    Create a JPG object from a local PDF file
    Input:
        f: Local path to PDF file
    Output:
        d: Dictionary of JPG objects
    """
    d = dict()
    filepath = f
    assert os.path.exists(f)
    with wd.Image(filename=f, resolution=200) as img:
        page_images = []
        for page_wand_image_seq in img.sequence:
            page_wand_image = wd.Image(page_wand_image_seq)
            page_jpeg_bytes = page_wand_image.make_blob(format="jpeg")
            page_jpeg_data = io.BytesIO(page_jpeg_bytes)
            page_image = Image.open(page_jpeg_data)
            page_images.append(page_image)
    d['page_count'] = len(page_images)
    d['pages'] = page_images
    return d


def process_request( json, data, headers, params ):
    """
    Helper function to process the request to Project Oxford

    Parameters:
    json: Used when processing images from its URL. See API Documentation
    data: Used when processing image read from disk. See API Documentation
    headers: Used to pass the key information and the data type request
    """

    retries = 0
    result = None

    while True:
        response = requests.request( 'post', _url, json = json, data = data, headers = headers, params = params )

        if response.status_code == 429:
            print( "Message: %s" % ( response.json() ) )
            if retries <= _maxNumRetries:
                time.sleep(1)
                retries += 1
                continue
            else:
                print( 'Error: failed after retrying!' )
                break
        elif response.status_code == 202:
            result = response.headers['Operation-Location']
        else:
            print( "Error code: %d" % ( response.status_code ) )
            print( "Message: %s" % ( response.json() ) )
        break
    return response.json()


class AzureBlob():
    """Wrapper around blob object."""
    def __init__(self, name, key):
        self.blob = BlockBlobService(
            account_name = name,
            account_key = key
        )
        self.containers = self.blob.list_containers()

    def container_files(self, c):
        return self.blob.list_blobs(c.name)


def main():
    client = py.MongoClient(os.environ['MONGO_URI'])
    db = client.ch

    ch = AzureBlob(os.environ['BLOB_NAME'], os.environ['BLOB_KEY'])
    blob_file = db.docs.find_one({'filetype': 'pdf', 'doctype': 'annual-returns'})

    print(blob_file['container'], blob_file['blob_file'])

    ch.blob.get_blob_to_path(
            blob_file['container'],
            blob_file['blob_file'],
            blob_file['filename']
        )

    pages = create_jpg(blob_file['filename'])
    print(pages['page_count'])
    print(pages['pages'])


if __name__ == "__main__":
    main()


"""
local_file  = '/home/gavin/Projects/ds-hack/blob-store/' + blob_files[0][1]
"""

