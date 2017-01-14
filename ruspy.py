#!/usr/bin/python

import requests
import time
import webbrowser
import os
import json
import sys
from pytextbelt import Textbelt

# Phone number: ie. 1234567890
phone_num = '<PHONE NUMBER>'

# Semester code: ie. 12017 or 92017
semester = '<SEMESTER CODE>' 

# Campus code: ie. NB (New Brunswick), NK (Newark), CM (Camden)
campus = '<CAMPUS CODE>'

# Grad. level code: ie. U (Undergraduate), G (Graduate)
level = '<GRAD LEVEL>'

# Checks if the course section is open
def checkSection(course, course_num, section_num):
    if course['courseNumber'] == course_num:
        for section in course['sections']:
            if section['number'] == section_num:
                if section['openStatus'] == True:
                    course = {
                            'title': course['title'],
                            'section': section['number'],
                            'index': section['index']
                    }
                    remove_course_titled(course['title'])
                    return course

def message(subjects):

    deleted = False
    courses_available = []

    # Stops when all wanted courses open
    while True:
        print 'Checking for open sections...',
        
        for subject in subjects:
            url = 'http://sis.rutgers.edu/soc/courses.json?subject=' + subject['subject'] + '&semester=' + semester + '&campus=NB&level=' + level
            
            for course in subject['courses']:
                r = requests.get(url)
                recipient = Textbelt.Recipient(phone_num, 'us')

                if r.status_code == 200:
                    soc = r.json()

                    # Adds open courses into courses_available to use as info for the message
                    for c in soc:
                        temp = checkSection(c, course['course_num'], course['section_num'])
                        course_exists = False

                        # Determines if returned value is valid and if it does not already exist
                        if temp is not None:
                            deleted = True
                            if len(courses_available) > 0:
                                for i in courses_available:
                                    if temp['title'] == i['title']:
                                        course_exists = True
                            if not course_exists:
                                courses_available.append(temp)
                else:
                    print 'Error in requesting course schedules'
                    print 'STATUS CODE: ' + str(r.status_code)
                    print ''

        print 'CHECK DONE'
        if deleted == True:
            print 'Successfully removed course from list...'
            deleted = False

        # Opens browser to Webreg and sends link as message
        if len(courses_available) > 0:
        
            # Generates registration link
            indeces = ''
            for course in courses_available:
                indeces += course['index']
                if course is not courses_available[len(courses_available)-1]:
                    indeces += ','

            link = 'https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas&semesterSelection=' + semester + '&indexList=' + indeces

            # Converts link to shortened link to pass message char limit
            shortlink = None
            l = requests.get('http://tinyurl.com/api-create.php?url=' + link)
            if l.status_code == 200:
                shortlink = l.text

            # Prints out all open courses to console
            print ''
            for course in courses_available:
                print course['title'] + ' is available'
            print 'Registration Link: ' + link

            # Opens browser to Webreg
            print 'Opening browser to registration page...',
            try:
                webbrowser.open(link, new=2, autoraise=True)
                print 'DONE'
            except webbrowser.error:
                print webbrowser.error

            # Sends message to user
            message = '\nCourses available!\nRegistration Link: ' + shortlink

            response = recipient.send(message)
            if response['success']:
                print 'Message sent'
            else:
                print 'Message failed to send'
                print 'Trying again in 2 minutes...'
                time.sleep(120)
                response = recipient.send(message)
                if response['success']:
                    print 'Message resent'
                else:
                    print 'Message failed to send'

            # Stops script when no courses to watch
            if len(subjects) == 0:
                return True
            else:
                return False

        # Wait one minute before rechecking
        time.sleep(60)

# Gets user choice
def get_choice(prompt, expected_chars):
    expected_chars = expected_chars.lower()
    done = False
    chars = []
    while not done:
        user_input = raw_input(prompt)
        user_input = user_input.strip()
        user_input = user_input.lower()
        for char in expected_chars:
            if user_input == char:
                done = True
        if not done:
            print ''
            print 'Invalid input.'
            print ''
    return user_input
 
# Gets a number input
def get_code(prompt, code_len, isdigit):
    user_input = ''
    if isdigit:
        while not user_input.isdigit() or len(user_input) <> code_len:
            user_input = raw_input(prompt)
            if not user_input.isdigit() or len(user_input) <> code_len:
                print 'Invalid input. Please enter a number of length ' + str(code_len) + '.'
    else:
        while len(user_input) <> code_len:
            user_input = raw_input(prompt)
            if len(user_input) <> code_len:
                print 'Invalid input. Please enter a number of length ' + str(code_len) + '.'

    return user_input

# Adds a course to subjects and returns subjects
def add_course(subjects):
    print ''
    subject_code = None
    course_code = None
    section_code = None
    done = False
    while not done:
        subject_code = get_code('Subject Code: ', 3, True)

        # Checks if the subject code is valid
        url = 'http://sis.rutgers.edu/soc/courses.json?subject=' + subject_code + '&semester=' + semester + '&campus=NB&level=' + level
        r = requests.get(url)
        if r.status_code == 200:
            if r.text == '[]':
                print 'Subject code does not exist'
                continue
        else:
            print 'Error in retrieving data from WebReg'
            print 'Exitting application...'
            print ''
            sys.exit()

        course = None
        while course is None:
            course_code = get_code('Course code: ', 3, True)
            courses = r.json()
            for c in courses:
                if c['courseNumber'] == course_code:
                    course = c
            if course is None:
                print 'Course code does not exist'
                continue

        section = None
        while section is None:
            section_code = get_code('Section Number: ', 2, False)
            for s in course['sections']:
                if s['number'] == section_code:
                    section = s['number']
            if section is None:
                print 'Section number does not exist'
                continue

        done = True

    course = {
        "course_num": course_code,
        "section_num": section_code,
        "title": course['title']
    }
    subject_exists = False
    for subject in subjects:
        if subject['subject'] == subject_code:
            subject_exists = True
            subject['courses'].append(course)
    if not subject_exists:
        subjects.append(
            {
                "courses": [course],
                "subject": subject_code
            }
        )

    print course['title'] + ' added'
    return subjects

# Removes a course from subjects and returns subjects
def remove_course(subjects):
    print ''
    subject = None
    subject_pos = -1
    course = None
    subject_code = None
    course_code = None
    done = False

    while subject is None:
        subject_code = get_code('Subject Code: ', 3, True)
        for s in subjects:
            subject_pos += 1
            if s['subject'] == subject_code:
                subject = s
        if subject is None:
            print 'Subject not found in data'

    while course is None:
        course_code = get_code('Course code: ', 3, True)
        for c in subject['courses']:
            if c['course_num'] == course_code:
                course = c
        if course is None:
            print 'Course not found in data'

    subjects[subject_pos]['courses'].remove(course)

    if len(subjects[subject_pos]['courses']) == 0:
        subjects.remove(subject)

    print course['title'] + ' removed'

    return subjects

# Removes course with course as input
def remove_course_titled(title):
    subjects = get_data()
    subpos = -1
    retval = []
    deleted = []
    for subject in subjects:
        subpos += 1
        for course in subject['courses']:
            if course['title'] == title:
                subjects[subpos]['courses'].remove(course)
                deleted.append(title)
    for subject in subjects:
        if len(subject['courses']) == 0:
            subjects.remove(subject)
    retval.append(subjects)
    retval.append(deleted)
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    file = open('subjects.json', 'w')
    file.write(json.dumps(subjects))
    file.close()
    return retval

# Prints all courses watched
def print_courses(subjects):
    print ''
    print 'COURSES WATCHED'
    for subject in subjects:
        for course in subject['courses']:
            print ''
            print course['title']
            print 'Subject code: ' + subject['subject']
            print 'Course code: ' + course['course_num']
            print 'Section code: ' + course['section_num']

# Gets data on courses 
def get_data():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    # Get data from file
    file = open('subjects.json', 'r')
    subjects = file.read()
    if len(subjects) == 0 or len(json.loads(subjects)) == 0:
        raise IOError

    return json.loads(subjects)

# Controls the script
def script_control():
    # Write new file if it doesn't exist and prompt user for data
    subjects = []

    # Ask for subjects and courses
    choice = None
    while choice <> 'q':
        print ''
        print 'What would you like to do?'
        print 'Check for open sections [C]'
        print 'Add course [A]'
        print 'Remove course [R]'
        print 'Print watched courses [P]'
        print 'Quit [Q]'
        choice = get_choice('Enter input: ', 'carqp')

        if choice <> 'q':
            try:
                subjects = get_data()
            except IOError:
                if choice <> 'a':
                    print ''
                    print 'No data found'
            if subjects is not None and len(subjects) <> 0:
                if choice == 'c':
                    done = message(subjects)
                    while not done:
                        time.sleep(60)
                        try:
                            subjects = get_data()
                        except IOError:
                            print ''
                            print 'No courses to check...'
                            print 'Exiting application...'
                            print ''
                            sys.exit()
                        done = message(subjects)
                    if done:
                        print ''
                        print 'No courses left to check...'
                        print 'Exiting Application...'
                        print ''
                        sys.exit()
                elif choice == 'r':
                    subjects = remove_course(subjects)
                elif choice == 'p':
                    print_courses(subjects)
            if choice == 'a':
                subjects = add_course(subjects)

        if choice == 'a' or choice == 'r':
            file = open('subjects.json', 'w')
            file.write(json.dumps(subjects) + '\n')
            file.close()

print ' '
print 'COURSE CHECKER'
print ' '
print 'Starting Application...'

try:
    script_control()
except KeyboardInterrupt:
    print ''
    print ''
    print 'Exitting Application...'
    print ''
    sys.exit()

print ''
print 'Exitting Application...'
print ''
sys.exit()


