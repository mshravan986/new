#!/usr/bin/env python

import boto3
import os
import datetime
import logging
import pandas as pd

from dateutil.relativedelta import relativedelta

CURRENT_MONTH = "true"
if CURRENT_MONTH == "true":
    CURRENT_MONTH = True
else:
    CURRENT_MONTH = False

#cd = boto3.client('ce', 'us-east-1')
#ec2 = boto3.resource('ec2', region_name='us-west-2')
#for instance in ec2.instances.all():
#    print(instance, instance.tags)
#vpc_address = ec2.VpcAddress('allocation_id')
#print(vpc_address)

class CostExplorer:
    """Retrieves BillingInfo checks from CostExplorer API
    >>> costexplorer = CostExplorer()
    >>> costexplorer.addReport(GroupBy=[{"Type": "DIMENSION","Key": "SERVICE"}])
    >>> costexplorer.generateExcel()
    """
    print("test-1")    
    def __init__(self, CurrentMonth=False):
        #Array of reports ready to be output to Excel.
        self.reports = []
	print("test")
        self.client = boto3.client('ec2', region_name='us-west-2')
        self.end = datetime.date.today().replace(day=1) - datetime.timedelta(days=1) # last day of last month
        self.riend = datetime.date.today()
        if CurrentMonth or CURRENT_MONTH:
            self.end = self.riend
        self.start = (datetime.date.today() - relativedelta(months=+12)).replace(day=1) #1st day of month 11 months ago
        print(self.start)
        self.ristart = (datetime.date.today() - relativedelta(months=+11)).replace(day=1) #1st day of month 11 months ago
        print(self.ristart)
	try:
            self.accounts = self.getAccounts()
	    print(self.accounts)		
        except:
            logging.exception("Getting Account names failed")
            self.accounts = {}
    def getAccounts(self):
        accounts = {}
        client = boto3.client('mshravan986@gmail.com', region_name='us-west-2')
	print(client)
        paginator = client.get_paginator('list_accounts')
        response_iterator = paginator.paginate()
        for response in response_iterator:
            for acc in response['Accounts']:
                accounts[acc['Id']] = acc
        return accounts
        results = []
        response = self.client.get_reservation_coverage(
            TimePeriod={
                'Start': self.ristart.isoformat(),
                'End': self.riend.isoformat()
            },
            Granularity='MONTHLY'
        )
        results.extend(response['CoveragesByTime'])
        while 'nextToken' in response:
            nextToken = response['nextToken']
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': self.ristart.isoformat(),
                    'End': self.riend.isoformat()
                },
                Granularity='MONTHLY',
                NextPageToken=nextToken
            )
	    response = client.list_aws_service_access_for_organization(
                NextToken='string',
                MaxResults=123
            )
            results.extend(response['CoveragesByTime'])
            if 'nextToken' in response:
                nextToken = response['nextToken']
                print(nextToken)  
            else:
                nextToken = False
    def addReport(self, Name="Default",GroupBy=[{"Type": "DIMENSION","Key": "SERVICE"},], 
    Style='Total', NoCredits=True, CreditsOnly=False, UpfrontOnly=False):
        results = []
        if not NoCredits:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': self.start.isoformat(),
                    'End': self.end.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=[
                    'UnblendedCost',
                ],
                GroupBy=GroupBy
            )
        else:
            Filter={"Not": {"Dimensions": {"Key": "RECORD_TYPE","Values": ["Credit", "Refund", "Upfront"]}}}
            if CreditsOnly:
                Filter={"Dimensions": {"Key": "RECORD_TYPE","Values": ["Credit", "Refund"]}}
            if UpfrontOnly:
                Filter={"Dimensions": {"Key": "RECORD_TYPE","Values": ["Upfront",]}}
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': self.start.isoformat(),
                    'End': self.end.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=[
                    'UnblendedCost',
                ],
                GroupBy=GroupBy,
                Filter=Filter
            )

        if response:
            results.extend(response['ResultsByTime'])
            
            while 'nextToken' in response:
                nextToken = response['nextToken']
                response = self.client.get_cost_and_usage(
                    TimePeriod={
                        'Start': self.start.isoformat(),
                        'End': self.end.isoformat()
                    },
                    Granularity='MONTHLY',
                    Metrics=[
                        'UnblendedCost',
                    ],
                    GroupBy=GroupBy,
                    NextPageToken=nextToken
                )
                results.extend(response['ResultsByTime'])
                if 'nextToken' in response:
                    nextToken = response['nextToken']
                else:
                    nextToken = False
        # Now we should have all records, lets setup a waterfall datagrid
        #{key:value for (key,value) in dictonary.items()}
        rows = []
        for v in results:
            row = {'date':v['TimePeriod']['Start']}
            for i in v['Groups']:
                key = i['Keys'][0]
                if key in self.accounts:
                    key = self.accounts[key][ACCOUNT_LABEL]
                row.update({key:float(i['Metrics']['UnblendedCost']['Amount'])}) 
            if not v['Groups']:
                row.update({'Total':float(v['Total']['UnblendedCost']['Amount'])})
            rows.append(row)  

        df = pd.DataFrame(rows)#index=[i['date'] for i in rows]
        df.set_index("date", inplace= True)
        df = df.fillna(0.0)
        
        if Style == 'Change':
            dfc = df.copy()
            lastindex = None
            for index, row in df.iterrows():
                if lastindex:
                    for i in row.index:
                        try:
                            df.at[index,i] = dfc.at[index,i] - dfc.at[lastindex,i]
                        except:
                            logging.exception("Error")
                            df.at[index,i] = 0
                lastindex = index
        df = df.T    
        
        self.reports.append({'Name':Name,'Data':df})
def main_handler(event=None, context=None): 
    costexplorer = CostExplorer(CurrentMonth=False)
    costexplorer.addReport(Name="Accounts", GroupBy=[{"Type": "DIMENSION","Key": "LINKED_ACCOUNT"}],Style='Total')
if __name__ == '__main__':
    main_handler()        
