#! /usr/bin/env python3

import re
import cv2
import numpy         as np
import pytesseract   as pt
import pyzbar.pyzbar as pz
from PIL         import Image
from pathlib     import Path
from collections import namedtuple

# todo

Field = namedtuple('Field', 'par, line, word, left, top, width, height, conf, text')
months = {'jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'}

chars_alpha = 'abcdefghijklmnopqrstuvwxyz' \
            + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
chars_digit = '1234567890'
chars_punct = '/()?,- '
chars_block = chars_alpha + chars_digit + chars_punct

re_name = re.compile(r'[^A-Za-z ]')
re_npid = re.compile(r'[^0-9P]')
re_date = re.compile(r'[^A-Za-z0-9\?\/]')
re_addr = re.compile(r'[^A-Za-z0-9, ]')


def main():
  for num in range(9):
    image = load_image(f'test/{num:02}.png')
    text  = image_to_text(image)
    if text:
      for k,v in text.items(): print(k, v)
    

def image_to_text(image):
  gray   = to_gray(image)
  code, angle = get_barcode(gray)
  if code is None: return None, None
  label  = get_label(gray, angle, code)
  blabel = binarize(label)
  block  = segment_label(blabel)
  ptdata = block_to_ptdata(block, charlist=chars_block)
  fields = ptdata_to_fields(ptdata)
  fields = validate_fields(fields, block.shape[0])
  text   = fields_to_text(fields)
  text   = validate_text(text)
  return text, code['data']


def load_image(f):
  return np.array(Image.open(f))


def save_image(i,f):
  Path(f).parent.mkdir(parents=True, exist_ok=True)
  Image.fromarray(i).save(f)


def save_text(t,f):
  Path(f).parent.mkdir(parents=True, exist_ok=True)
  Path(f).write_text(t)


def to_gray(image):
  # read and convert to 8-bit gray
  if len(image.shape) > 2: return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  else:                    return image


def draw_fields(image, fields):
  # convert image to color and draw rectangle for each field bounding box
  color = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
  for f in fields:
    top_left  = (f.left        , f.top         )
    bot_right = (f.left+f.width, f.top+f.height)
    color = cv2.rectangle(col, top_left, bot_right, (0,255,0))
  return color


def draw_barcode(image, angle, code, num):
  # convert image to color and draw rectangle for barcode bounding box and poly
  rect = code['bbox']
  pts = np.array( [[x,y] for x,y in code['poly']] ).reshape( (-1,1,2) )
  rot = rotate_image(image, angle)
  rot = cv2.cvtColor(rot, cv2.COLOR_GRAY2BGR)
  bar = cv2.rectangle(rot, rect, (0,255,0))
  bar = cv2.polylines(bar, [pts], True, (255,0,0))
  return bar


def get_barcode(image):
  def extract_objects(objs):
    return [{'data': (obj.data).decode('u8'),
             'type':  obj.type,
             'bbox':  obj.rect,
             'poly':  obj.polygon} 
             for obj in objs]

  def search_rotation(image, arange):
    return {angle: extract_objects(pz.decode(rotate_image(image, angle))) 
            for angle in arange}

  # coarse
  barcodes = search_rotation(image, np.arange(-60, 61, 15))
  d = {angle: codes[0]
       for angle, codes in barcodes.items()
       if len(codes) and codes[0]['bbox'].width > codes[0]['bbox'].height}

  height, coarse = max(sorted((v['bbox'].height,k) for k,v in d.items()))
  #print(f'coarse: {coarse}')

  # fine
  barcodes = search_rotation(image, np.arange(coarse-7, coarse+7.5, 0.5))
  d = {angle: codes[0] 
       for angle, codes in barcodes.items()
       if len(codes)}

  height, fine   = max(sorted((v['bbox'].height,k) for k,v in d.items()))
  #print(f'fine: {fine}')
  return d[fine], fine


def get_label(image, angle, barcode):
  image = rotate_image(image, angle)
  # crop image from barcode dims
  l = barcode['bbox'].left
  t = barcode['bbox'].top
  w = barcode['bbox'].width
  x = w
  cx = int(l + w/2)
  cy = int(t + w/8)
  label_x  =      int(x * 13/ 8)  # ~ 1024 / 630
  label_y  =      int(x * 40/63)  # ~  400 / 630
  label_cx = cx + int(x *  5/21)  # ~  150 / 630
  label_cy = cy - int(x *  8/45)  # ~  112 / 630
  y0 = int(label_cy - label_y/2)
  y1 = int(label_cy + label_y/2)
  x0 = int(label_cx - label_x/2)
  x1 = int(label_cx + label_x/2)
  
  return image[max(0,y0):min(image.shape[0],y1),
               max(0,x0):min(image.shape[1],x1)]


def rotate_image(image, angle, center=None):
  # rotate image and pad to prevent clipping image
  if angle == 0: 
    return image
  if center is None:
    center = tuple(i//2 for i in image.shape[::-1])
  cx,cy = center
  mat = cv2.getRotationMatrix2D(center, angle, 1.0)
  cos = np.abs(mat[0,0])
  sin = np.abs(mat[0,1])
  # compute the rotated image dimensions
  dy,dx = image.shape
  dxr = int((dy * sin) + (dx * cos))
  dyr = int((dy * cos) + (dx * sin))
  # adjust the rotation matrix for center translation
  mat[0,2] += (dxr/dx * cx) - cx
  mat[1,2] += (dyr/dy * cy) - cy
  return cv2.warpAffine(image, mat, (dxr, dyr), borderValue=255)


def binarize(image, low=0, high=254):
  crop = image[image.shape[0]//4:3*image.shape[0]//4,
               image.shape[1]//4:3*image.shape[1]//4]
  t, _ = cv2.threshold(crop, low, high, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
  _, b = cv2.threshold(image,  t, high, cv2.THRESH_BINARY)
  return b


def segment_label(label, pad=5):
  # segment barcode and text from label
  blabel = binarize(label)
  clabel = blabel[:,blabel.shape[1]//4:3*blabel.shape[1]//4]
  rows   = np.mean(clabel, axis=1).astype('u1')
  brows  = rows < 250
  # convert true/false array to segments of (length, first row)
  edges = [0,] \
        + [i+1 for i in range(len(brows)-1) if brows[i] != brows[i+1]] \
        + [len(brows),]
  # sort segments by length; largest first
  segments = sorted([(j-i, i) for i,j in zip(edges[:-1],edges[1:]) if brows[i]], 
               reverse=True)

  # return label above barcode if detected; default to top half of image
  if len(segments):  barcode = segments[0]
  else:              barcode = label[:label.shape[0]//2,:]
  return label[:barcode[1],:]


def block_to_ptdata(image, charlist=None):
  if charlist: config = f'--psm 6 -c tessedit_char_whitelist="{charlist}"'
  else:        config = f'--psm 6'
  return pt.image_to_data(image, lang='eng', config=config)


def ptdata_to_fields(data, delim='\t'):
  lines = data.splitlines()
  t  = namedtuple('Data', map(str.strip, lines[0].split(delim)))
  ts = list(map(t._make, [map(str.strip, l.split(delim)) for l in lines[1:]] ))
  return [Field(int(r.par_num), int(r.line_num), int(r.word_num), 
                int(r.left), int(r.top), int(r.width), int(r.height), int(r.conf), 
                r.text)
            for r in ts if int(r.conf) > -1 and r.text != '']


def validate_fields(fields, height):
  # filter by height
  fields = [f for f in fields if (f.height / height) > 0.13] # f.conf >= 20 and

  # group by lines
  lines = {(f.par, f.line): [] for f in fields}
  for f in fields:
    lines[(f.par, f.line)].append(f)
  lines = list(lines.values())

  return {'name':  lines[0]     ,
          'npid': [lines[1][0],],
          'date':  lines[1][1:] ,
          'addr':  lines[2]     }


def fields_to_text(fields):
  # join words if they are adjacent or overlapping
  text = {}
  for k,line in fields.items():
    fields = [field for field in line]
    words  = []
    i = 0
    while i < len(fields):
      if i+1 < len(fields) and fields[i].left + fields[i].width >= fields[i+1].left:
        words.append(fields[i].text + fields[i+1].text)
        i += 2
      else:
        words.append(fields[i].text)
        i += 1

    text[k] = ' '.join(words)

  return text


def validate_text(text):
  text['name'] = re_name.sub('', text['name'])
  text['npid'] = re_npid.sub('', text['npid'])
  text['date'] = re_date.sub('', text['date'])
  text['addr'] = re_addr.sub('', text['addr'])

  day,mon,year = text['date'].split(r'/')
  text['sex']  = year[-1]
  year = year[:-1]
  if r'?' in day  or int(day) > 31:               day  = '??'
  if r'?' in mon  or mon.lower() not in months:   mon  = '??'
  if r'?' in year or not 1920 < int(year) < 2025: year = '????'
  text['date'] = '/'.join((day,mon,year))

  return text


if __name__ == '__main__':
  main()

# done
#   optimize angle search
#     coarse rotation
#       search by 15 deg rotations
#       save dict of {angle: code if code.width > code.height}
#       pick optimal angle for code.height (most complete barcode)
#     fine tune rotation
#       search by 0.5 deg
#   preprocess label before ocr
#     binarize
#       exclude 255 background
#       crop before otsu
#   refine label extraction
#     better bounds of barcode
#       rotation search
#         height sensitive to incomplete corners
#       crop too aggressive on left side
#         correct ratio from 8/5 to 13/8 calculated from 01.png 1024/629
#   segmentation
#     text from fields
#       eliminate text with height < expected from label height
#         im  h    text          noise
#         00  186  32-38  .1720  
#         01  231  36-40  .1558  
#         03  159  23-32  .1447  02  05  08  12  16  02  19  08
#         04  122  20-34  .1639  28
#         05  218  38-44  .1784  
#         06  217  40-52  .1843  01
#         07  217  39-50  .1797  
#         08  224  39-67  .1741  
#         09  228  39-64  .1711  
#       use par,line,word numbers
#         condense par,line to line
#       find matching pid : barcode
#         line 2
#       pick adjacent lines above and below
#         lines 1-3
#   feed rows back into pt with custom character lists/format
#   use charlist in block_to_text
#   fields_to_text
#     join adjacent text boxes
#     remove confidence check

#  # save debug output
#  if debug:
#    name    = f'{num:02}'
#    fields  = '\n'.join(map(str, fields))
#    #overlay = draw_fields(block, fields)
#    save_image(gray,   f'gray/{name}.png')
#    save_image(label,  f'label/{name}.png')
#    save_image(blabel, f'label_bin/{name}.png')
#    save_image(block,  f'block/{name}.png')
#    save_text(fields,  f'fields/{name}.txt')
#    #save_img(overlay,f'overlay/{name}.png')
