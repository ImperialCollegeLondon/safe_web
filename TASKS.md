### Implementation questions

* Outputs - can anyone add any outputs to their/any projects (currently only the person who uploaded the project).
* Users - do you want members of the public to have access to user details

### Tedious prelaunch tasks 

* Classification of projects to tag
* User list consolidation - emails
* Existing project member roles and assign coordinators
* Species photos - replace with ones we have any right to
* Tag existing projects with new tags and revamp 'Ecological monitoring' page to 'Research areas'
 * Outputs - create an Abstract and Twitter description.
                 - update existing output descriptions to match.
 


### Programming tasks

* Data structure sketch.
* Passwords, match SALT/HASH to Earthcape
* Project, project\_members, auth\_users all need UID
* Lock down removal of project members and visit members in existing visits and reservations
* Fix wiki path to Wiki (apache config, I think, maybe change dir name)
* Diagrams of processes
* Email templates - centralise and log
* Apply consistent zero= values for IS_IN_DB() to make it look nice
* Think about whether we can use placeholder text in forms to get a nicer feel
     form.custom.widget.test.update(_placeholder="Anonymous")
     form.custom.widget.tm_home["_placeholder"] = "Home Team Name"
* Project versioning
Check out:
http://web2py.com/books/default/chapter/29/07/forms-and-validators#Record-versioning

* Project carousel
* Add workplace pages to MySAFE
* Add discussion board

### Tasks to classify from meeting with Rob

 * Home page.
 * Replace maps with new versions
 * Species profiles - make
 * Outputs/Wiki/Data to "Data and results" main menu
 * Add market to MySAFE
 * Make all project and output links
 * Word restrictions on project case 300, 500.

* Add research tags to volunteers sought from project.
* Show group membership on Profile.

### Passwords

Web2Py Admin on EC2 - GlenfiddichWednesdays
Superuser on Dokuwiki - CaolIlaMercredi

curl --request GET \
--url 'https://us6.api.mailchimp.com/3.0/campaigns' \
--user 'anystring:c028335ab2baec6ee9710ed466cd9146-us6' \
--include


curl --request GET \
--url 'https://us6.api.mailchimp.com/3.0/campaigns/d654cc960c/content' \
--user 'anystring:c028335ab2baec6ee9710ed466cd9146-us6' \
--include

