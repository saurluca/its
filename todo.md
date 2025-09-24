\**Feature*s\*

- [ ] Skill system ???
- [ ] Topic system ???
- [ ] Prompt for specifc tasks / topics
  - [ ] Search and filter relevant chunks
  - [ ] Include prompt in question generation?
- [ ] Improve user management
  - [ ] Overview page of who is in what repo
  - [ ] remove users
  - [ ] modify acces rights
- [ ] Teacher Dashboard to see student perofrmance in calss
- [ ] Student dashboard to track progress
- [ ] certify teacher repo
- [ ] Dashboard to see reports
- [ ] Hide / show tasks and or units

**Improvements**

- [ ] Checkbox to create unit when uploading document
- [ ] Disable button that can not be used (e.g. sutyd evalute beofre you selected something)
- [ ] Enable Formula conversion for math in docling
  - [ ] enable
  - [ ] test
- [ ] Update UX for long uploads / generaiton
  - [ ] Update message to fit, instead of succes
  - [ ] message on sucess
  - [ ] send erorr message if not working (tasks/upload)
  - [ ] error on empty document / no chunks
- [ ] Smoothen onboarding experince with login, currently a bit of a wall
- [ ] Multi document Upload
- [ ] Remove teacher / student toggle as it is useless lol, or do it depending on repo read / write access
- [ ] Replace Close button in show source on study page with X as in the reposiroty page

**Fixes**

- [ ] Cannot delete uni repo etc if a report was made due to model links
- [ ] Repo deleted but not direclty updated in sidebar
- [ ] wierd formating when selctin more then one document in generate tasks modal

**Ideas**

- [ ] Show original document instead of parsed docuemtn to student
  - [ ] Save original document
  - [ ] (optional) search chunk in og document
  - [ ] Display

decil-c38
![[Pasted image 20250916140525.png]]

https://tutorshop.ethz.ch/

Skills:

problems:
how to share skills across repositories? just name? but then waht is a desciription???

A repository has multiple skills.
The multiple skills of a user are defined via the repositories he is in.
The skill progression is absolute based on a set number of tasks per skill.
The progress of a user in a skill is across repositories.
Each task is assigned to exactly one skill.
Skills are uniquely identified by their names, in such a way skills can be shared across repos.

Keep track of how many times a task has been answered / correct / incorrectly / semi by a user in integer field. later used for task recommendation.
Skills are optional for a task/ repository.
Documents don't care about skills.

recommendation, the lower a skill of a task the higher its recomendation chance. The less a user has seen a task or the worse he is at answering it, the more likely he is to see the task.

---

Where do I add & modify skills -> tasks page?
Show skill where ucrrntly / multiple choise open quesitkns is written.??
Where can I as a student see my skills and my progress -> own user page

So when I upload a document I want skills to already be suggest for each task in the task creation process.

- If it is the first document, create new skills based on content?
- if skills already exist in repo, take those and propose new ones?

Flow:

- how to create skills, manually and automatically
- how to assign skills to tasks
- how see my own skill progress

---

See how well students perform on each question

Predifene or freely define skills?
What level / granularity?

Workflow:
make repo -> upload document -> suggest skills based on existing skills an docuemnt -> teacher approve skills -> generate tasks -> suggest skills -> approve tasks and skills

Skills are optional

For the teacher it would be interesting to see what skills students already have, what they did before.

add course model inbetwen repo and document. does not have it own documents.
add descirption to reposiorty so people can dersibe what they teach and what the target audience and skill level is.

student dashboard - with skill and progress

teacher dashboard - progress of class

two stages:
define skills for repo based on existjg skils in system and based on document
second stage generate tasks and assing skilsl to that

role based access system

differnetiate skill repos and normal repos

certify repositories by official teachers vs student made repositories

vissualy indiacte / mark cetrified repis by cfieteifed teahcers

put document upload button under document list

rename repositorires to course
add layer section, which is a group of tasks
documents only in courses.
tasks only relate to sections and not direclty to classes
Show sections, documents and skills in a course in the overview page.
teacher dashboard per per course to see skill progress
Show per task sucesss rate just on tasks page

rework reposorty overview so that you select a specific course and then go into its detail view sections, skills, documents. incluidng settings for description

1. Deployment
2. Skills
3. Rework course strucutre
4. role based on ceritfied users
5. teacher / student dashboard
