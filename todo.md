**Daniel**
- [ ] Prompt for specifc tasks / topics
	- [ ] Search and filter relevant chunks
	- [ ] Include prompt in question generation?
- [ ] Admin dashboard
	- [ ] with reports
	- [ ] option to ceritfy certain users as teachers
- [ ] Hide / show tasks and or units


**Luca**
- [ ] Seperate user mangamnet page per reposiotry including
	- [ ] REMOVEING useres
	- [ ] adding useres 
	- [ ] modify access rigths




**Improvements UI**
- [x] Hide study button without tasks
- [x] Disable button that can not be used (e.g. sutyd evalute beofre you selected something)
- [ ] Button to leave reposiorty on main page
- [ ] Update UX for long uploads / generaiton
	- [ ] Update message to fit, instead of succes
	- [ ] message on sucess
	- [ ] send erorr message if not working (tasks/upload)
	- [ ] error on empty document / no chunks
	- [ ] Dont ping backend all the time, espcaily when it is already long finished.
	- [ ] if document has 0 or 1 chunk ( like 1 line document), genraiton fails because no chunks, dont make fail silent
	- [ ] stop pollin when you got stuff
- [x] Remove teacher / student toggle as it is useless lol, or do it depending on repo read / write access
- [x] Replace Close button in show source on study page with X as in the reposiroty page
- [x] Use same html iwer in study and repository
- [x] Ensure chekcox in document selito nalways have same size
- [x]  wierd formating when selctin more then one document in generate tasks modal


**Improvements Backend**
- [x] Fix local docling tag, from latest to main
- [ ] Enable Formula conversion for math in docling 
	- [x] enable
	- [ ] test
- [ ] Cannot delete uni repo etc if a report was made due to model links
- [ ] Fix deletion repdencies when deleting for example repos
- [ ] Repo deleted but not direclty updated in sidebar



**For Later**
- [ ] Skill system ???
- [ ] Topic system ???
- [ ] Show original document instead of parsed docuemtn to student
	- [ ] Save original document
	- [ ] (optional) search chunk in og document
	- [ ] Display
- [ ] Teacher Dashboard 
	- [ ] see student performance in class
- [ ] Student dashboard
	- [ ] track personal progress
- [ ] Show producet before signup, people dont want to sign up otherwise, to much effoer
	- Potnetial let them run on localstorage first?
	- Smoothen onboarding experince with login, currently a bit of a wall
	- Landing page?
- [ ] Switch to redis or something similar for long runing tasks like exercise generation and document upload / conversion
	- [ ] Multi document Upload
- [ ] Pictures extract from documents
	- [ ] And can be used in tasks


**Possible Additions**



  
