# This is all the relevant code from my .ipynb file:
# https://github.com/martin-martin/cleaning-las-vegas/blob/master/las_vegas_summary.ipynb

# Hope the format is alright and I'd be glad for many comments regarding my code! :)
# Do help me to learn to become better!

##############################################################################################
######################################### EXPLORING ##########################################
##############################################################################################

import os
import xml.etree.cElementTree as ET
import pprint
import pandas as pd
import re

# importing the data
las_vegas_osm = 'las-vegas_nevada.osm'
## for testing and developing purposes, uncomment the truncated version:
#las_vegas_osm = 'LV_truncated.osm'

def count_tags(filename):
    """Creates a dictionary with the tags present in the dataset, alongside a count for each."""
    tag_dict = {}
    for event, elem in ET.iterparse(filename):
        if elem.tag not in tag_dict:
            tag_dict[elem.tag] = 1
        elif elem.tag in tag_dict:
            tag_dict[elem.tag] += 1
    return tag_dict

# checking out some basic stats
file_size = os.path.getsize(las_vegas_osm)
print 'File Size in Bytes:', file_size
print 'File Size in MB:   ', file_size / (2**20)

las_vegas_osm_dict = count_tags(las_vegas_osm)
las_vegas_osm_tags = pd.Series(las_vegas_osm_dict, name='tags and their amounts')
print las_vegas_osm_tags


# auditing the street names and creating the dictionary I will use through the analysis
def audit_street_type(street_types, expected, street_name):
    """Checks whether the last word of a string is in a list, if not, it appends to a list.

    Checks the last word of a string against a provided list of expected street types,
    if it isn't it add the street name to a dictionary that is passed as an input.
    Reference: https://www.udacity.com/course/viewer#!/c-ud032-nd/l-768058569/e-865319708/m-900198650
    """
    street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
    found = street_type_re.search(street_name)
    if found:
        street_type = found.group()
        if street_type not in expected:
            if street_type not in street_types:
                street_types[street_type] = [street_name]
            else:
                street_types[street_type].append(street_name)


def collect_way_types(filename, expected_types):
    """Searches the tag attributes in an OSM file for street names and adds them to a dictionary.

    Takes as input a file and a list of expected types,
    Calls the audit_street_type() function,
    Returns a dictionary with street types mapping to a list of street name occurences.
    Reference: https://www.udacity.com/course/viewer#!/c-ud032-nd/l-768058569/e-865319708/m-900198650
    """
    street_types = {}
    for event, elem in ET.iterparse(filename, events=('start',)):
        if elem.tag == 'way':
            for tag in elem.iter('tag'):
                if tag.attrib['k'] == 'name':
                    street_name = tag.attrib['v']
                    audit_street_type(street_types, expected_types, street_name)
    return street_types


# choosing to exclude the common street types
# at first I run the function without excluding anything
common_types = []
street_types = collect_way_types(las_vegas_osm, common_types)

# While working with the truncated version of the dataset, I chose the threshold of 7
# through checking the results. 10 returned an empty list, 5 included 'Vegas'
# - which I believe is not a valid street name :)
threshold = 7
# updating the common_types variable
for key, value in street_types.items():
    if len(value) > threshold:
        common_types.append(key)
# calling the function again, now excluding some common street types
street_types = collect_way_types(las_vegas_osm, common_types)


# a function to investigate specific elements (which I did way too much...)
def find_something(filename, regex):
    """ Prints the OSM elements matching the regex, and a link to view them online. Returns None."""
    import re
    flag = False
    for event, elem in ET.iterparse(filename, events=('start',)):
        if elem.tag == 'way':
            for tag in elem.iter('tag'):
                if tag.attrib['k'] == 'name':
                    if re.search(regex, ET.tostring(tag)):
                        print "Check ID online at: http://www.openstreetmap.org/way/" + elem.attrib['id'] + '\n'
                        ET.dump(elem)
                        flag = True
    if not flag:
        print "No matching Element was found."

# after checking some elements and the street_types list I concluded that
# these can be safely excluded, because they represent (most probably) valid ways
valid_ways = ['Aisle', 'Alley', 'Bypass', 'Channel', 'Highway', 'Interconnect', 'Loop', 'Monorail', 'Path', 'Paths',
             'Route', 'Speedway', 'Walk']
nature_ways = ['Falls', 'Forest', 'Lake', 'Shore', 'Spillway', 'Stream', 'River', 'Thrust', 'Wash']

# creating a new 'exclude' variable and recalculating the street_types dict
exclude = common_types + valid_ways + nature_ways
street_types =  collect_way_types(las_vegas_osm, exclude)





##############################################################################################
########################################## CLEANING ##########################################
##############################################################################################

from pprint import pprint
import xml.etree.cElementTree as ET
import re
import codecs

############## step 1 - reduce the file size ##############

OSM_FILE = las_vegas_osm
NEW_FILE = 'cleaning_1.osm'

def get_ways(osm_file, tags=('node', 'way', 'relation')):
    """Filters an OSM file and yields the 'way' elements.

    Reference: https://discussions.udacity.com/t/changing-attribute-value-in-xml/44575/6
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            if elem.tag == 'way':
                yield elem
                root.clear()

# creating a new file holding only 'way' elements
with open(NEW_FILE, 'w') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output.write('<osm>\n  ')

    for i, element in enumerate(get_ways(OSM_FILE)):
        output.write(ET.tostring(element, encoding='utf-8'))

    output.write('</osm>')


# setting the input file to the previous output file
OSM_FILE = NEW_FILE
NEW_FILE = 'cleaning_2.osm'
common_and_valid_ways = exclude

def select_some_way_elems(osm_file, excluded_ways):
    """Yields way elements which last word (usually the street type) is not in a list to exclude."""
    import re
    street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag == 'way':
            for tag in elem.iter():
                try:
                    if tag.attrib['k'] == 'name':
                        street_name = tag.attrib['v']
                        found = street_type_re.search(street_name)
                        street_type = found.group()
                        if street_type not in excluded_ways:
                            yield elem
                            root.clear()
                except:
                    continue

# writing a new document that consists only of those way elements that select_some_way_elems() yields.
with open(NEW_FILE, 'w') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output.write('<osm>\n  ')

    for i, element in enumerate(select_some_way_elems(OSM_FILE, common_and_valid_ways)):
        output.write(ET.tostring(element, encoding='utf-8'))

    output.write('</osm>')


############## step 2 - starting to clean elements ##############

# defining some functions to perform cleaning on the OSM elements

def modify_file(filename, function, *args):
    """Modifies a file according to the output of a function.

    Takes as input a file name, a function and its arguments.
    Runs the (cleaning) function and writes the output back into the file,
    using a temporary file object as intermediate step.
    Reference:
    http://stackoverflow.com/questions/17646680/writing-back-into-the-same-file-after-reading-from-the-file
    """
    import tempfile
    import sys
    temp_file = tempfile.NamedTemporaryFile(mode = 'r+')
    input_file = open(filename, 'r')
    for i, element in enumerate(function(*args)):
        temp_file.write(ET.tostring(element, encoding='utf-8'))
    input_file.close()
    temp_file.seek(0)
    with open(filename, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<osm>\n  ')
        for line in temp_file:
            f.write(line)
        f.write('</osm>')
    temp_file.close()


def get_id(filename, regex):
    """Returns a list of the IDs of the element(s) matching the specified regex somewhere in their tags."""
    import re
    elem_id_list = []
    for event, elem in ET.iterparse(filename, events=('start',)):
        if elem.tag == 'way':
            for tag in elem.iter('tag'):
                if tag.attrib['k'] == 'name':
                    if re.search(regex, ET.tostring(tag)):
                        elem_id_list.append(elem.attrib['id'])
    return elem_id_list


def substitute_attrib_value(osm_file, before, after, attrib_key, tags=('way', 'node', 'relation')):
    """Changes text in an attribute to a string defined in 'after'.

    Changes the text in a specified attribute of a 'way' tag
    that contains the string variable defined in 'before' for a new string defined in 'after'.
    Reference:
    https://discussions.udacity.com/t/changing-attribute-value-in-xml/44575/6
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            if elem.tag == 'way':
                for tag in elem.iter('tag'):
                    # not changing the original TIGER data
                    if ('tiger:' not in tag.attrib['k'] and
                        re.search(before, ET.tostring(tag))):
                        tag.set(attrib_key, after)
            yield elem
            root.clear()


def substitute_smth(osm_file, before, after, attrib_key):
    """Wrapper function: Calls substitute_attrib_value() and modify_file().

    Substitutes a 'way' tag attribute for another and writes the changes back.
    """
    substitute_attrib_value(osm_file, before, after, attrib_key, tags=('way', 'node', 'relation'))
    modify_file(osm_file, substitute_attrib_value, osm_file, before, after, attrib_key)


def add_attribute(osm_file, elem_id, attrib_key, attrib_value, tags=('way', 'node', 'relation')):
    """Adds a tag Element with attribute and value to a 'way' Element specified through an ID.

    Reference:
    https://discussions.udacity.com/t/changing-attribute-value-in-xml/44575/6
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            if elem.attrib['id'] == elem_id:
                try:
                    for tag in elem.iter('tag'):
                        if tag.attrib['k'] == attrib_key and tag.attrib['v'] == attrib_value:
                            raise Exception('AttributePresentError')
                    ET.SubElement(elem, 'tag', k=attrib_key, v=attrib_value)
                except Exception:
                    print "The attributes %s=%s are already present in this Element."%(attrib_key, attrib_value)
                    continue
            yield elem
            root.clear()


def add_smth(osm_file, elem_id, attrib_key, attrib_value):
    """Wrapper function: Calls add_attribute() and modify_file().

    Adds an attribute with value to an existing "way" tag, writes the changed ET back to the file."""

    add_attribute(osm_file, elem_id, attrib_key, attrib_value, tags=('way', 'node', 'relation'))
    modify_file(osm_file, add_attribute, osm_file, elem_id, attrib_key, attrib_value)


# setting the input file to the previous output file, to write back into the same file
OSM_FILE = 'cleaning_2.osm'

# performing some automated cleaning
for area in street_types['Estates']:
    for elem_id in get_id(OSM_FILE, area):
        add_smth(OSM_FILE, elem_id, 'place', 'suburb')
        add_smth(OSM_FILE, elem_id, 'area', 'yes')

add_smth(OSM_FILE, '27575073', 'building', 'yes')
substitute_smth(OSM_FILE, 'Wonderful Day Driive', 'Wonderful Day Drive', 'v')
substitute_smth(OSM_FILE, 'Wanderlust', 'Wanderlust Court', 'v')
substitute_smth(OSM_FILE, 'Seven Oaks', 'Seven Oaks Way', 'v')
substitute_smth(OSM_FILE, 'Padero', 'North Padero Drive', 'v')
substitute_smth(OSM_FILE, 'Scottyboy', 'Scottyboy Drive', 'v')
substitute_smth(OSM_FILE, 'Seashore', 'Seashore Drive', 'v')
substitute_smth(OSM_FILE, 'S FLore del Sol', 'S Flore del Sol Street', 'v')
substitute_smth(OSM_FILE, street_types['Avenmue'][0], 'West Fenway Park Avenue', 'v')




############################## UPDATING CLEANING FUNCTIONS ##############################

# adapting the function with the newly learned aspects to exclude more inappropriate 'way' tags
def collect_way_types(filename, expected_types):
    """Searches the tag attributes in an OSM file for street names and adds them to a dictionary.

    Takes as input a file and a list of expected types, also excludes certain parameters that
    either represent a (foreign-language) common street name, or are 'way' tags that are no streets.
    Calls the audit_street_type() function,
    Returns a dictionary with street types mapping to a list of street name occurences.
    """
    street_types = {}
    # added these common non-english street names that appear at the beginning of the string
    non_eng_street_names = ['Avenida', 'Via', 'Camino', 'Calle', 'Vista', 'Placida']
    # here are some attributes that I found define non-street ways, so I exclude Elements containing them
    non_street_attribs = ['area', 'building', 'amenity', 'golf', 'railway']
    for event, elem in ET.iterparse(filename, events=('start',)):
        flag = False
        if elem.tag == 'way':
            for tag in elem.iter('tag'):
                if (tag.attrib['k'] in non_street_attribs) and (tag.attrib['v'] != 'no'):
                        flag = True
                for non_eng_name in non_eng_street_names:
                    # if a street starts with one of the non-eng names, it is excluded
                    if tag.attrib['v'].startswith(non_eng_name):
                        flag = True

            if flag == False:
                for tag in elem.iter('tag'):
                    if tag.attrib['k'] == 'name':
                        street_name = tag.attrib['v']
                        audit_street_type(street_types, expected_types, street_name)
    return street_types

# a dictionary of individually-checked elements that are valid streets,
# but do not have right away obvious valid street-type-names
all_fine = {'Access' : street_types['Access'],
            'Oak' : street_types['Oak'],
            'Oasis' : street_types['Oasis'],
            'Paseo' : street_types['Paseo'],
            'Pines' : street_types['Pines'],
            'Cottage' : street_types['Cottage'],
            'Point' : street_types['Point'],
            'Portico' : street_types['Portico'],
            'Reef' : street_types['Reef'],
            'Sawtooth' : street_types['Sawtooth'],
            'Sierra' : street_types['Sierra'],
            'Solano' : street_types['Solano'],
            'Star' : street_types['Star']}

# elements that should have a tag with 'area=yes' and 'place=suburb' added
add_area_suburb = {'Homestretch' : street_types['Homestretch'],
                  'Homes' : street_types['Homes'],
                  'Paradise' : street_types['Paradise'],
                  'Somerset' : street_types['Somerset']}

# elements that should have a tag with 'area=yes' and one with 'building=yes' added
add_area_building = {'Alex' : street_types['Alex']}

# elements that should have a tag with 'area=yes' added
add_area = {'P' : street_types['P'],
            'Wilderness' : street_types['Wilderness']}

# examples of abbreviations that come up and could be substituted
substitute = {'Ave' : street_types['Ave'],
              'Hwy' : street_types['Hwy'],
              'Rd' : street_types['Rd']}



############## step 3 - some more cleaning ##############

# add area=yes
type_dict = add_area
for key, value in type_dict.items():
    for v in enumerate(value):
        name = v[1]
        for elem_id in get_id(OSM_FILE, name):
            add_smth(OSM_FILE, elem_id, 'area', 'yes')

# add area=yes, building=yes
type_dict = add_area_building
for key, value in type_dict.items():
    for v in enumerate(value):
        name = v[1]
        for elem_id in get_id(OSM_FILE, name):
            add_smth(OSM_FILE, elem_id, 'area', 'yes')
            add_smth(OSM_FILE, elem_id, 'building', 'yes')

# add area=yes, place=suburb
type_dict = add_area_suburb
for key, value in type_dict.items():
    for v in enumerate(value):
        name = v[1]
        for elem_id in get_id(OSM_FILE, name):
            add_smth(OSM_FILE, elem_id, 'area', 'yes')
            add_smth(OSM_FILE, elem_id, 'place', 'suburb')

# extend street name abbreviations
import re
map_dict = {'Rd' : 'Road', 'Hwy' : 'Highway', 'Ave' : 'Avenue'}
type_dict = substitute
street_re = re.compile(r'[^ ]+[ ]', re.IGNORECASE)

for key, value in type_dict.items():
    for v in enumerate(value):
        old_name = v[1]
        re_li = re.findall(street_re, old_name)
        new_name = ''.join(re_li) + map_dict[key]
        substitute_smth(OSM_FILE, old_name, new_name, 'v')

# add valid streets to the 'exclude' list
for key in all_fine.keys():
    if key not in exclude:
        exclude.append(key)


# computing the 'street_types' dict anew with the updated elements, function and 'exclude' list
street_types = collect_way_types(OSM_FILE, exclude)






##############################################################################################
######################### MERGING THE CHANGES WITH THE ORIGINAL FILE #########################
##############################################################################################


# creating a parsed ET from the OSM XML elements that were being cleaned
tree_changes = ET.ElementTree(file=OSM_FILE)
chang_root = tree_changes.getroot()
# creating a list containing all the 'way' elements (= all elements)
changed_elems = chang_root.findall('way')
# creating a dictionary mapping the elements' IDs to the element objects
changes_dict = {}
for elem in changed_elems:
    changes_dict[elem.attrib['id']] = elem

def merge_changes(osm_file, changes):
    """Merges the changes applied on the street names back into the original OSM file structure, creating a new file."""
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'start' and elem.tag == 'way':
            current_id = elem.attrib['id']
            if current_id in changes.keys():
                elem = changes[current_id]
        if event == 'end':
            yield elem
            root.clear()


ORIG_FILE = las_vegas_osm
NEW_FILE = 'LV_applied_changes.osm'

# running the merge_changes() function, creating a new file that includes the changes computed above
with open(NEW_FILE, 'w') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output.write('<osm>\n  ')
    for i, element in enumerate(merge_changes(ORIG_FILE, changes_dict)):
        output.write(ET.tostring(element, encoding='utf-8'))
    output.write('</osm>')






##############################################################################################
##################################### PORTING TO MONGODB #####################################
##############################################################################################

# Code taken from Lesson 6 and adapted to my situation
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json

problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
CREATED = [ "version", "changeset", "timestamp", "user", "uid"]

def shape_element(element):
    """Shapes an OSM element according to certain parameters into a valid JSON object.

    Reference: https://www.udacity.com/course/viewer#!/c-ud032-nd/l-768058569/e-865240067/m-863660253
    """
    node = {}
    if element.tag == "node" or element.tag == "way":
        node['created'] = {}
        node['visible'] = 'true'
        node['type'] = element.tag
        for key, value in element.attrib.iteritems():
            if key in CREATED:
                node['created'][key] = value
            elif key != 'lat' and key != 'lon':
                node[key] = value
        try:
            node['pos'] = [float(element.attrib['lat']), float(element.attrib['lon'])]
        except:
            pass
        if element.tag == 'way':
            node['node_refs'] = {}
            nd_list = []
            for nd in element.iter('nd'):
                nd_list.append(nd.attrib['ref'])
            node['node_refs'] = nd_list

        # creating the additional dicts
        for child in element:
            if child.tag == 'tag':
                attrib_key = child.attrib['k']
                attrib_value = child.attrib['v']
                if re.search(r'(\w+:){2}', attrib_key):
                    continue
                if re.search(r':', attrib_key):
                    separate_by_colon_re = re.compile(r'([\w]+[^:\n])')
                    key_parts_list = re.findall(separate_by_colon_re, attrib_key)
                    main_key = key_parts_list.pop(0)
                    # removing the main key
                    if len(key_parts_list) == 1:
                        secondary_key = key_parts_list.pop(0)
                        if main_key == 'addr':
                            if 'address' in node:
                                node['address'][secondary_key] = attrib_value
                            else:
                                node['address'] = {}
                                node['address'][secondary_key] = attrib_value
                        else:
                            if main_key in node and type(node[main_key]) == dict:
                                node[main_key][secondary_key] = attrib_value
                            ### NOTE: Some keys I create with regex as keys for dict might already exist as
                            ### keys one level up. Therefore I added this to not lose the information from there
                            else:
                                main_key = main_key+'dict'
                                node[main_key] = {}
                                node[main_key][secondary_key] = attrib_value
                            if main_key not in node:
                                node[main_key] = {}
                                node[main_key][secondary_key] = attrib_value
                else:
                    node[attrib_key] = attrib_value
        return node
    else:
        return None

def process_map(file_in, pretty = False):
    """Takes an OSM file as input, restructures the Elements to JSON objects and writes a new .json file."""
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
            for _, element in ET.iterparse(file_in):
                    el = shape_element(element)
                    if el:
                            data.append(el)
                            if pretty:
                                    fo.write(json.dumps(el, indent=2)+"\n")
                            else:
                                    fo.write(json.dumps(el) + "\n")
    return data

# calling the function to create the .json file
json_struct = process_map('las-vegas_nevada.osm')
