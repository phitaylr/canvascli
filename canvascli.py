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

@cli.command(help="Initialize a course with modules, units, etc.")
@click.argument('course', nargs=1, type=int)
@click.argument('n', nargs=1, type=int)
@click.argument('unitname')
@pass_config
def courseinit(config,course, n, unitname):
    apipost("%scourses/%s/folders" %(config.apiurl,course),{'name': 'Course Information','parent_folder_path': '/',},config)

    modules=[]
    #setup module organization
    for i in range(1,n+1):
        pages=[]
        module = apipost("%scourses/%s/modules" %(config.apiurl,course),{'module[name]': '%s %s' %(unitname,i), 'module[position]': '%s' %(i)},config)
        modules.append(module)
        mid = module['id']

        #make pages
        with open('intropagetext.html', 'r') as intropagetextfile:
            intropagetext = intropagetextfile.read()

        #pages.append(apipost("%scourses/%s/pages" %(config.apiurl,course),{'wiki_page[title]': '%s %s: Objectives' %(unitname,i), 'wiki_page[body]': intropagetext },config))
        # pages.append(apipost("%scourses/%s/pages" %(config.apiurl,course),{'wiki_page[title]': '%s %s: Vocabulary' %(unitname,i), 'wiki_page[body]': 'Add content vocabulary here.' },config))
        # pages.append(apipost("%scourses/%s/pages" %(config.apiurl,course),{'wiki_page[title]': '%s %s: Tasks' %(unitname,i), 'wiki_page[body]': 'Add links to required tasks here.' },config))
        #pages.append(apipost("%scourses/%s/pages" %(config.apiurl,course),{'wiki_page[title]': '%s %s: Resourses' %(unitname,i), 'wiki_page[body]': 'Add links to additional resources here.' },config))

        for page in pages:
            apipost("%scourses/%s/modules/%s/items" %(config.apiurl,course,mid),{'module_item[title]': '%s' %(page['title']), 'module_item[type]': 'Page', 'module_item[page_url]': '%s' %(page['url'])},config)


        # SubHeaders
        apipost("%scourses/%s/modules/%s/items" %(config.apiurl,course,mid),{'module_item[title]': 'Tasks', 'module_item[type]': 'SubHeader',},config)
        apipost("%scourses/%s/modules/%s/items" %(config.apiurl,course,mid),{'module_item[title]': 'Graded Items', 'module_item[type]': 'SubHeader',},config)



        #make folder
        apipost("%scourses/%s/folders" %(config.apiurl,course),{'name': '%s %s' %(unitname,i),'parent_folder_path': '/'},config)

    #make home page
    # homepagetext="<h3>%ss</h3>\n<ul>" %(unitname)
    # for module in modules:
    #     homepagetext+=" <li><a href=\"https://tvs.instructure.com/courses/%s/modules/%s\"> %s</a></li>" %(course, module['id'], module['name'])
    # homepagetext+=" </ul>"
    # page=apipost("%scourses/%s/pages" %(config.apiurl,course),{'wiki_page[title]': 'Home Page', 'wiki_page[body]': homepagetext, 'wiki_page[published]': 'true', 'wiki_page[front_page]': 'true' },config)
    #

@cli.command(help="Get a list of all projects/quizzes/tests in a given term.")
@click.argument('term', nargs=1, type=int)
@pass_config
def listassignments(config,term):
    courses = apiget("%saccounts/1/courses" %(config.apiurl),{'enrollment_term_id': term},config)
    output=""
    if(len(courses)>0):
        for c in courses:
            numa=0
            assigntext=""
            assignments = apiget("%scourses/%s/assignments" %(config.apiurl,c['id']),{'enrollment_term_id': term},config)
            for a in assignments:
                if(a['published'] and ("quiz" in a['name'] or "Quiz" in a['name'] or "Test" in a['name'] or "test" in a['name'] or "project" in a['name']
                or "Project" in a['name'] or "exam" in a['name'] or "Exam" in a['name'])):
                    assigntext+=("\n\t%s" %(a['name']))
                    numa+=1
            if assigntext != "":
                output += "%s\n%s" %(c['name'], assigntext)
                click.echo(output)
    else:
        click.echo("No courses in term!")
    click.echo(output)

@cli.command(help="Make assignments for a course. (Philip Custom)")
@click.argument('course', nargs=1, type=int)
@click.argument('titleprefix', nargs=1, )
@click.argument('numberofassignments', nargs=1, type=int)
@click.argument('descurl', nargs=1, )
@pass_config
def makeassignments(config,course,titleprefix,numberofassignments,descurl,):
    for i in range(1,numberofassignments+1):
        a=apipost("%scourses/%s/assignments" %(config.apiurl,course), {'assignment[name]': '%s%s' %(titleprefix, i), 'assignment[submission_types][]': 'on_paper', 'assignment[points_possible]': '0', 'assignment[description]': 'Go <a href=\"%s\">here</a> for more details.' %descurl, 'assignment[published]': 'true',  }, config)
        print(a)


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
