class TemplateReader:
    def __init__(self):
        pass

    def read_course_template(self,country_template):
        try:
            if (country_template=='India_template'):
                email_file = open("email_templates/India_Template.html", "r")
                email_message = email_file.read()
            elif (country_template=='NotIndia_template'):
                email_file = open("email_templates/NotIndia_Template.html", "r")
                email_message = email_file.read()
            elif (country_template=='Worldwide_Template'):
                email_file = open("email_templates/Worldwide_Template.html", "r")
                email_message = email_file.read()
            return email_message
        except Exception as e:
            print('The exception is '+str(e))
