import json
import requests
import os
import csv
from pycipapi.cipapi_client import CipApiClient
import yaml


""" 

Get a list of cases from GMS dev that have a last status repi

For each case get the panel ID and version and look up in panel app the count of green genes

Write an output file that can be used to check against what happens when the SoF HTML is downloaded from the Portal

"""

credentials = os.getenv('GEL_CREDENTIALS')
credentials = yaml.load(open(credentials, 'r'), Loader=yaml.FullLoader)
dev_credentials = [x for x in credentials if x['name'] == 'cipapi-dev'][0]

c = CipApiClient(url_base=dev_credentials['host'],
                 user=dev_credentials['username'],
                 password=dev_credentials['password'])

def get_panel_info_for_case(case):

    output = {'case_id': case.interpretation_request_id, 'case_version': case.version, 'panel_info': []}

    panels = case.pedigree.analysisPanels

    for panel in panels:
        output['panel_info'].append({'panelName': panel.panelName, 'panelVersion': panel.panelVersion})

    return output




def applied_version_green_genecount(panel_id, panel_version):

    url = 'https://panelapp.genomicsengland.co.uk/api/v1/panels/{panel_id}/?version={panel_version}'.format(
        panel_id=panel_id,
        panel_version=panel_version)
    panel_version = requests.get(url=url).json()
    panelapp_green_gene_list = []
    for gene in panel_version['genes']:
        if gene["confidence_level"] == "3":
            panelapp_green_gene_list.append(gene['gene_data']["gene_symbol"])
    return len(set(panelapp_green_gene_list))

def update_case_info_with_panel_count(case_info):

    for panel in case_info['panel_info']:
        gene_count = applied_version_green_genecount(panel['panelName'], panel['panelVersion'])
        panel.update({'gene_count': gene_count})

    return case_info

def write_output_file(fname, data_list, category):

    with open(fname, 'w') as csv_file:
        line_writer = csv.writer(csv_file, delimiter=",")
        line_writer.writerow(['case_id', 'case_version', 'panel_id', 'panel_version', 'green_gene_count', 'url'])
        for case in data_list:
            print(case)
            for panel in case['panel_info']:
                portal_url = "https://cipapi-gms-dev.gel.zone/interpretationportal/{category}/participant/{case_id}-{case_version}".format(category=category,
                                                                                                                                           case_id=case['case_id'],
                                                                                                                                    case_version=case['case_version'])
                line_writer.writerow([case['case_id'],
                                      case['case_version'],
                                      panel['panelName'],
                                      panel['panelVersion'],
                                      panel['gene_count'],
                                      portal_url])
    return fname


if __name__ == "__main__":

    for category in ['gms', '100k']:
        fname = "CIPAPI-680_{category}_panel_gene_count_checking.csv".format(category=category)
        cases = c.get_cases(last_status='report_sent',
                            program='rare_disease',
                            cip='congenica',
                            category=category,
                            tags='E2E_TESTING_REFERRAL')

        data_list = []
        for case in cases:
            print(case.interpretation_request_id, case.last_status, case.cip)
            case = c.get_case(case_id=case.interpretation_request_id, case_version=case.version)
            case_info = get_panel_info_for_case(case)
            d = update_case_info_with_panel_count(case_info)
            data_list.append(d)
        write_output_file(fname=fname, data_list=data_list, category=category)









