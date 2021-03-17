import json
import requests
import os
from pycipapi.cipapi_client import CipApiClient
import yaml

cred_dict = yaml.load(open(os.getenv('GEL_CREDENTIALS')), Loader=yaml.FullLoader)
cipapi_credentials = {entry['name']: entry for entry in cred_dict}
username = cipapi_credentials['cipapi-dev']['username']
password = cipapi_credentials['cipapi-dev']['password']
c = CipApiClient(url_base='https://cipapi-gms-test.gel.zone/', user=username, password=password)

caselist = ['651-1']

def getIR(case):
    ir, version = case.split('-')
    case = c.get_case(case_id=ir, case_version=version, reports_v6='true')
    interpretation_request = case.interpretation_request_data['json_request']
    return interpretation_request

def get_coverage_data(interpretation_request):
    panels_genecount = []
    coverage_json = interpretation_request['genePanelsCoverage']
    for panel in coverage_json:
        del coverage_json[panel]['SUMMARY']
        panels_genecount.append({'panelId': panel,
                                 'genecount': len(coverage_json[panel]),
                                 'gene_list': coverage_json[panel].keys()})
    return panels_genecount


def signedoff_green_genecount(paneldata):
    panelapp_green_genecounts = []
    for panel in paneldata:
        signedoffpanel = requests.get('https://panelapp.genomicsengland.co.uk/api/v1/panels/signedoff/{}/'.format(panel['panelId'])).json()
        # panel_name = signedoffpanel['name']
        panelapp_green_gene_list = []
        for gene in signedoffpanel['genes']:
            if gene["confidence_level"] == "3":
                panelapp_green_gene_list.append(gene['gene_data']["gene_symbol"])
        panelapp_green_genecounts.append({'panelID': panel['panelId'],
                                          'green_gene_count': len(set(panelapp_green_gene_list)),
                                          'gene_list': panelapp_green_gene_list })
    return panelapp_green_genecounts

for case in caselist:
    IR = getIR(case)
    paneldata = get_coverage_data(IR)
    panelappRefData = signedoff_green_genecount(paneldata)
    pairs = zip(paneldata, panelappRefData)
    notequal = [(x, y) for x, y in pairs if x != y]
    if not notequal:
        print("Gene count in coverage data matches the green gene count in signed off panels")
    else:
        for item in notequal:
            print("Panel with id {} has {} genes in coverage data, while the number of green genes in the gms signed off panel is {}".format(item[0]['panelId'], item[0]['genecount'], item[1]['green_gene_count']))
            diff_1 = set(item[0]['gene_list']).difference(set(item[1]['gene_list']))
            print('coverage genes not in panel app green genes n =',len(diff_1), diff_1)
            diff_2 = set(item[1]['gene_list']).difference(set(item[0]['gene_list']))
            print('panel app green genes not in coverage n =', len(diff_2), diff_2 )
