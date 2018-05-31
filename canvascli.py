import click
import json, csv
import requests
import time
import pandas
import datetime
import numpy as np
from pathlib import Path

apiurl=""
apiauth=""
verbose = False;

class Config(object):

    def __init__(self):
        apiurl, apiauth=loadCredentials()
        self.apiurl = apiurl
        self.apiauth = apiauth
        self.verbose = False
        self.archive_term = 90

pass_config = click.make_pass_decorator(Config, ensure=True)

@click.group()
@click.option('--verbose', is_flag=True)
@pass_config
def cli(config,verbose):
    """Canvas Command Line Interface"""
    config.verbose=verbose


@cli.command(help="Delete unused courses from Unused Courses csv report from Canvas")
@click.argument('input', type=click.Path(exists=True))
@pass_config
def deleteunused(config,input):
    click.echo("WARNING: This will delete all courses listed in %s" %input)
    if (click.confirm('Do you want to continue?', abort=True)):
        reader = csv.reader(open(input, 'r'))
        courses = {}
        for row in reader:
            courses[row[0]] = row

        for course in courses:
            if(courses[course][4]=='unpublished'):
                print("Deleting course: %s ... " %courses[course][3])
                apidelete("%scourses/%s" %(config.apiurl,course),{'event': 'delete'},config)


@cli.command(help="Delete all courses in a term")
@click.argument('term', type=int)
@pass_config
def deletecoursesbyterm(config,term):
    #get all courses in term
    courses = apiget("%saccounts/1/courses" %(config.apiurl),{'enrollment_term_id': term},config)


    click.echo("WARNING: This action will delete the following courses:")
    for course in courses:
        if(course['enrollment_term_id']==term):
            print(course['name'])

    if (click.confirm('Do you want to continue?', abort=True)):
        for course in courses:
            print("Deleting course: %s ... " %course['name'])
            apidelete("%scourses/%s" %(config.apiurl,course['id']),{'event': 'delete'},config)

@cli.command(help="Move courses to archived term")
@click.argument('courses', nargs=-1, type=int)
@pass_config
def archive(config,courses):
    for c in courses:
        #change term to archive term
        apiput("%scourses/%s" %(config.apiurl,c),{'course[term_id]': '%s' %config.archive_term},config)


@cli.command(help="Report published assignments with no due dates in term")
@click.argument('term', type=int)
@pass_config
def reportnoduedates(config,term):
    click.echo("Working... ")
    numc=0
    courses = apiget("%saccounts/1/courses" %(config.apiurl),{'enrollment_term_id': term},config)
    if(len(courses)>0):
        for c in courses:
            output=""
            numa=0
            assignments = apiget("%scourses/%s/assignments" %(config.apiurl,c['id']),{'enrollment_term_id': term},config)
            for a in assignments:
                if(a['due_at']==None and a['published']):
                    output+=("\n\t%s" %(a['name']))
                    numa+=1
            if(numa>0):
                if(numc==0):
                    click.echo("These assignments in term %s are published, but have no due date." %term)
                click.echo("%s %s" %(c['name'], output))
                numc+=1
        if(numc==0):
            click.echo("No assignments in term %s are published and do not ahve a due date." %term)
    else:
        click.echo("No courses in term!")

@cli.command(help="Prepare RenWeb export file")
@click.argument('input', type=click.Path(exists=True))
@pass_config
def renwebexport(config,input):
    df = pandas.read_csv(input)
    df = df.drop(['student id','course id','course sis', 'section', 'section id', 'term', 'term id', 'term sis', 'grading period set', 'grading period set id', 'current score','enrollment state'], axis=1)

    for col in df.columns:
        if "period id" in col or "unposted" in col or "final" in col:
            df=df.drop(col, axis=1)

    click.echo("Multiple grading periods found...")
    pds={}
    i=1
    for p in (df.columns):
        if ("student name" not in p and  "student sis" not in p and "course" not in p and "section sis" not in p ):
            click.echo("%s: %s" %(i,p[:-14]))
            pds[i]=p
            i+=1

    pd = click.prompt("Which grading period?", type=int)

    if int(pd) not in pds:
        click.echo("Sorry, that was not a choice. Please try again.")
        return


    for p in pds:
        if p != pd:
            df=df.drop(pds[p], axis=1)

    df.columns=['student_name','student_sis','course','section_sis','current_score']

    termid = click.prompt("What is the Canvas term identifier that should be removed? \n(e.g., \"1819_\")")

    #Drop NaNs
    df = df[pandas.notna(df['current_score'])]

    #strip canvas term identifier
    df['section_sis'] = df['section_sis'].map(lambda x: x.lstrip(termid))

    #export to xlsx
    outfile = Path('%s/Desktop/RenWeb %s.xlsx' %(str(Path.home()), input.split('/')[-1][:-4]))
    if outfile.exists():
        outfile = Path('%s/Desktop/RenWeb %s %s.xlsx' %(str(Path.home()), input.split('/')[-1][:-4], datetime.datetime.now()))

    writer = pandas.ExcelWriter(outfile)
    df.to_excel(writer,'canvas', index=False)
    writer.save()

    click.echo("File saved at: %s" %(outfile))



##########   API UTILITIES   ###########
def loadCredentials():
    with open('%s/.canvasclicred.json' %(str(Path.home())), 'r') as f:
        credentials = json.load(f)
    apiurl = credentials['url']
    apiauth = credentials['auth']
    return apiurl, apiauth

def apiget(url,params,config):
    headers={'Authorization': 'Bearer %s'%(config.apiauth),'per_page':'%s'%(1000),}
    params['per_page']=1000
    data=requests.get(url,params,headers=headers)
    if(config.verbose):
        print("%s %s:\n\t%s" %(url,params,data.text))
    return data.json()

def apipost(url,params,config):
    headers={'Authorization': 'Bearer %s'%(config.apiauth),'per_page':'%s'%(1000),}
    params['per_page']=1000
    data=requests.post(url,params,headers=headers)
    if(config.verbose):
        print("%s %s:\n\t%s" %(url,params,data.text))
    return data.json()

def apiput(url,params,config):
    headers={'Authorization': 'Bearer %s'%(config.apiauth),'per_page':'%s'%(1000),}
    params['per_page']=1000
    data=requests.put(url,params,headers=headers)
    if(config.verbose):
        print("%s %s:\n\t%s" %(url,params,data.text))
    return data.json()

def apidelete(url,params,config):
    headers={'Authorization': 'Bearer %s'%(config.apiauth),'per_page':'%s'%(1000),}
    params['per_page']=1000
    data=requests.delete(url,params=params,headers=headers)
    if(config.verbose):
        print("%s %s:\n\t%s" %(url,params,data.text))
    return data.json()
