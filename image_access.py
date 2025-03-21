from tifffile import TiffFile
import fsspec

from PIL import Image
import numpy as np
from io import BytesIO

class PyrTifAccessor:
    def __init__(self,s3_url):
        self.fs = fsspec.filesystem("s3",anon=True)
        
        self.url = s3_url

        self.infodict = {'series':[]}

        with self.fs.open(self.url, 'rb', block_size=1024) as fp:
            with TiffFile(fp) as tif:

                for ser in tif.series:
                    levels = {'levels':[]}
                    
                    for lev in ser.levels:
                        pages = {'pages':[]}
                        for page in lev.pages:
                            pages['pages'].append({
                                'imagewidth':page.imagewidth,
                                'tilewidth':page.tilewidth,
                                'tilelength':page.tilelength,
                                'dtype':page.dtype,
                                'compression':page.compression,
                                'samplesperpixel':page.samplesperpixel, # channels
                                'tiles_per_row': (page.imagewidth + page.tilewidth -1) // page.tilewidth,
                                'tiles_per_column': (page.imagelength+page.tilelength-1)//page.tilelength,
                            })
                        levels['levels'].append(pages)

                    self.infodict['series'].append(levels)


    def get_info(self,seriesnum=None,levelnum=None,pagenum=None):
        if seriesnum is None:
            return self.infodict
        if levelnum is None:
            return self.infodict['series'][seriesnum]
        if pagenum is None:
            return self.infodict['series'][seriesnum]['levels'][levelnum]
        return self.infodict['series'][seriesnum]['levels'][levelnum]['pages'][pagenum]
    
    def get_page(self,seriesnum,levelnum,pagenum):
        with self.fs.open(self.url, 'rb', block_size=4*1024) as fp:
            with TiffFile(fp) as tif:
                page = tif.series[seriesnum].levels[levelnum].pages[pagenum]
                return page.asarray()

    def get_tile(self,seriesnum,levelnum,pagenum,tile_index):
        np_tile = None
        with self.fs.open(self.url, 'rb', block_size=4*1024) as fp:
            with TiffFile(fp) as tif:
                
                page = tif.series[seriesnum].levels[levelnum].pages[pagenum]
                offset = page.dataoffsets[tile_index]
                byte_count = page.databytecounts[tile_index]

                fp.seek(offset)
                raw_tile = fp.read(byte_count)

                pil_tile = Image.open(BytesIO(page.jpegtables + raw_tile))
                np_tile = np.array(pil_tile)

        return np_tile


    def get_tiles(self,seriesnum,levelnum,pagenum,tile_index_list):

        out_tiles = {}
        with self.fs.open(self.url, 'rb', block_size=4*1024) as fp:
            with TiffFile(fp) as tif:
                
                page = tif.series[seriesnum].levels[levelnum].pages[pagenum]

                for tile_index in tile_index_list:
                    offset = page.dataoffsets[tile_index]
                    byte_count = page.databytecounts[tile_index]

                    fp.seek(offset)
                    raw_tile = fp.read(byte_count)

                    pil_tile = Image.open(BytesIO(page.jpegtables + raw_tile))
                    out_tiles[tile_index] = np.array(pil_tile)
        
        return out_tiles


    def get_region(self,seriesnum,levelnum,pagenum,left,top,width,height):
        
        info = self.infodict['series'][seriesnum]['levels'][levelnum]['pages'][pagenum]

        tile_width = info['tilewidth']
        tile_height = info['tilelength']

        tiles_per_row = info['tiles_per_row']

        x_tile_start = left // tile_width
        y_tile_start = top // tile_height
        x_tile_end = (left + width - 1) // tile_width
        y_tile_end = (top + height - 1) // tile_height

        # print(x_tile_start, y_tile_start, x_tile_end, y_tile_end)

        tile_rows = []
        for y_tile in range(y_tile_start, y_tile_end + 1):
            

            row_tile_indices = []
            for x_tile in range(x_tile_start, x_tile_end + 1):
                tile_index = y_tile * tiles_per_row + x_tile
                row_tile_indices.append(tile_index)
            
            row_tiles = self.get_tiles(seriesnum,levelnum,pagenum,row_tile_indices)
            tile_rows.append(np.hstack([row_tiles[tile_index] for tile_index in row_tile_indices])) # mosaic row_tiles

        full_region = np.vstack(tile_rows) # mosaic tile_rows

        offset_x = left - (x_tile_start * tile_width)
        offset_y = top - (y_tile_start * tile_height)
        roi = full_region[offset_y:offset_y + height, offset_x:offset_x + width]

        return roi