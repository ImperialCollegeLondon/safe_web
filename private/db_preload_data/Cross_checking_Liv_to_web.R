library('XLConnect')

# code to cross check what was extracted from the old website against Liv's records
setwd('/users/dorme/Research/SAFE/Web2Py/web2py/applications/SAFE_web/private/db_preload_data')


## PROJECTS according to Liv + Earthcape

	liv_project_wb <- loadWorkbook('liv_data_files/Projects.xlsx')
	liv_project_data <- readWorksheet(liv_project_wb, 1)
	
	# remove some empty lines
	liv_project_data[which(is.na(liv_project_data$Name)),]
	liv_project_data <- liv_project_data[- which(is.na(liv_project_data$Name)),]
	
	# remove some duplicates from liv's list
	liv_project_data <- liv_project_data[- which(liv_project_data$Code %in% c('SAFE-PRJ-49','SAFE-PRJ-17')),]
	
	
	web_project_data <- read.csv('project_inputs.csv', stringsAsFactors=FALSE, row.names=1)
	
	str(liv_project_data)
	str(web_project_data)
	
	# CURE SOME TYPOS/VARIANTS
	
	
	web_project_data$title[web_project_data$title == 'Effects of fragmentation on seedling recruitment, litter fall and decomposition ratesSeedling recruitment, litter fall and decomposition rates'] <-  "Effects of fragmentation on seedling recruitment, litter fall and decomposition rates"
	
	web_project_data$title[web_project_data$title  == "Woody debris as habitat for saproxylic arthropods"] <- "The role of woody debris as habitats for saproxylic arthropods"
	
	web_project_data$title[web_project_data$title  == "Ecology of a large squamate (Varanus salvator macromaculatus)"] <- "Investigating the ecology of a large squamate (Varanus salvator macromaculatus) in altered forest ecosystems, Sabah, Borneo, Malaysia."
	
	web_project_data$title[web_project_data$title  == "Using vocal fingerprints to monitor Bornean gibbons"] <- "Using vocal fingerprints to monitor Bornean gibbons (Hylobates muelleri) at the Stability of Altered Forest Ecosystems Project"
	
	web <- "Tropical Rainforest Dynamics And Its Effects On Insect Communities"
	liv <- "Tropical Rainforest Dynamics And Its Effects On Insect Communities In Sabah"
	web_project_data$title[web_project_data$title  == web] <- liv
	
	web <- "Tree girdling - BALI project"
	liv <- "Tree girdling – BALI project"
	liv_project_data$Name[liv_project_data$Name == liv] <- web
	
	web <-  'Impacts of tropical rainforest disturbance on mammalian parasitism rates'
	liv <- 'Impacts of tropical rainforest disturbance on mammalian parasitism rates\n'
	liv_project_data$Name[liv_project_data$Name == liv] <- web
	
	web <-  'Fragmentation effects on soil arthropods'
	liv <- 'Fragmentation and its effects on soil arthropods'
	web_project_data$title[web_project_data$title  == web] <- liv
	
	web <-  'Epiphytes in palm plantations: diversity and pest control'
	liv <- 'Biodiversity and ecosystem services in Malaysian oil palm'
	liv_project_data$Name[liv_project_data$Name == liv] <- web
	
	web <-  'Edge effects on insect herbivory rates and endophagous insect communities on two endemic dipterocarp species'
	liv <- 'The effects of fragmentation on insect herbivory rates and endophagous insect communities on two endemic dipterocarp species'
	liv_project_data$Name[liv_project_data$Name == liv] <- web
	
	web <- 'Composition and abundance of tropical freshwater vertebrate communities across a land use gradient'
	liv <- '\tComposition and abundance of tropical freshwater vertebrate communities across a land use gradient' 
	liv_project_data$Name[liv_project_data$Name == liv] <- web
	
	
	web <- 'Carbon budgets in modified forests'
	liv <- 'Intensive Carbon Monitoring In Sabah'
	liv_project_data$Name[liv_project_data$Name == liv] <- web
	
	liv_project_data$Name[liv_project_data$Name == "Retaining Riparian Reserves in Oil Palm Plantations and in a Highly Degraded Forest Area for Mammals Conservation"] <- "Retaining Riparian Reserves in Oil Palm Plantations and in a Highly Degraded Forest Area for Mammal Conservation"
	
	liv_project_data$Name[liv_project_data$Name == "Covariation between biodiversity and ecosystem functions across a modified tropical landscape: influences of environmental policies."] <- "Covariation between biodiversity and ecosystem functions"
	
	liv_project_data$Name[liv_project_data$Name == "Different land use effect on earthworms at SAFE Project site in Sabah, Borneo"] <- "Land use effect on earthworms"
	
	liv_project_data$Name[liv_project_data$Name == "Quantifying Predation Pressure Along a Gradient of Land Use Intensity in Sabah, Borneo"] <- "Quantifying Predation Pressure Along a Gradient of Land Use Intensity"
	
	liv_project_data$Name[liv_project_data$Name == "Functional diversity and community assembly patterns in ant (Hymenoptera: Formicidae) communities across a forest disturbance gradient in Sabah, Malaysia"] <- "Functional diversity and community assembly patterns in ant (Hymenoptera: Formicidae) communities across a forest disturbance gradient in Sabah"
	
	liv_project_data$Name[liv_project_data$Name == "Impacts of habitat sizes on butterfly communities at SAFE Project, Sabah"] <- "Impacts of habitat size on butterfly communities"
	
	liv_project_data$Name[liv_project_data$Name == "Parasite Biodiversity of Sabah Province, Borneo, Malaysia"] <- "Aquatic parasite biodiversity"
	
	liv_project_data$Name[liv_project_data$Name == "Quantifying Seed Dispersal Rate Amongst Vertebrates Vs Invertebrates Along a Land-Use Gradient"] <- "Partitioning Seed Dispersal Rate Amongst Vertebrates Vs Invertebrates Along a Land-Use Gradient"
	
	liv_project_data$Name[liv_project_data$Name == "Termite Fauna (Isoptera) at SAFE (Stability of Altered Forest Ecosystems) Experimental Plots, Tawau, Sabah, Malaysia"] <- "Variations in termite fauna (Isoptera) in altered forest habitats"
	
	
	# match liv to web scraped ones
	
	sanitise <- function(x){
		x <- tolower(x)
		x <- gsub("’","'", x)
		x <- gsub("[ .]+$","", x)
		x <- gsub("  +"," ", x)
	}
	
	liv_titles <- sanitise(liv_project_data$Name)
	web_titles <- sanitise(web_project_data$title)
	
	# Look for overlap on project titles
	intersect(web_titles, liv_titles)
	setdiff(web_titles, liv_titles)
	setdiff(liv_titles, web_titles)
	
	# extra ones from the web
	# Functional composition of trees and liana communities
	# "diversity of mosquito in safe project, sabah"  

	# Join on Liv's project codes for matching	
 	liv_project_data$join <- liv_titles
 	web_project_data$join <- web_titles
 	
 	web_project_data <- merge(web_project_data, 
 							  subset(liv_project_data, select = c('join','Code')), 
 							  by='join', all.x=TRUE)

	# reduce web scraped to key fields (these have been cleaned, so preferred over raw)
	to_drop <- which(names(web_project_data) %in% c('researchers', 'join',
					 'project_home_country', 'institution','sampling_scales',
					 'sampling_sites'))
	web_project_data <- subset(web_project_data, select = - to_drop)
	
	# now need to get Liv's extras into the same format as the web scraped ones
	liv_project_data$join <- liv_titles

	extra_projects <- liv_project_data[! liv_project_data$join %in% web_titles, ]
	str(extra_projects)
	
	extra_projects_format <- data.frame(title = extra_projects$Name,
										img_file = '',
										contact_email = extra_projects$ContactEmail,	
										methods = extra_projects$Description,
										rationale = extra_projects$Methods, 
										start_date = gsub(" 00:00:00", "", extra_projects$StartDate),
										end_date = gsub(" 00:00:00", "", extra_projects$EndDate),
										requires_ra = grepl('Research Assistant(s)', extra_projects$Resources),
										requires_vehicle = grepl('Vehicle', extra_projects$Resources),
										resource_notes = "",
										legacy_project_id = NA,
										Code = extra_projects$Code)	

	projects <- rbind(web_project_data, extra_projects_format)
	
	projects$Code[projects$title == 'Functional composition of trees and liana communities'] <- 'SAFE-WEB-1'
	projects$Code[projects$title == 'Diversity of mosquito in SAFE Project, Sabah'] <- 'SAFE-WEB-2'
	
	
## PEOPLE AND PROJECT MEMBERSHIP
	
	liv_user_wb <- loadWorkbook('liv_data_files/PersonCore.xlsx')
	liv_user_data <- readWorksheet(liv_user_wb, 1)[,1:4]
	
	str(liv_user_data)
	
	liv_member_wb <- loadWorkbook('liv_data_files/ProjectContact.xlsx')
	liv_member_data <- readWorksheet(liv_member_wb, 1)
	
	str(liv_member_data)
	
	# sanitising names
	sanitise <- function(x){
		x <- gsub('^\\W|\\W$','', x) # whitespace at either end
		x <- gsub("  +"," ", x) # multiple internal spaces
	}
	
	liv_user_data$FirstName <- sanitise(liv_user_data$FirstName)
	liv_user_data$LastName <- sanitise(liv_user_data$LastName)
	liv_member_data$Person <- sanitise(liv_member_data$Person)
	
	# some typos
	liv_user_data$LastName[liv_user_data$LastName == 'Arn The'] <- 'Arn Teh'
	liv_user_data$LastName[liv_user_data$LastName == 'MinSheng'] <- 'Min Sheng'
	liv_user_data$FirstName[liv_user_data$FirstName == 'Matheus'] <- 'Matheus Henrique'
	liv_member_data$Person[liv_member_data$Person == 'Rosahhah Williams'] <- 'Rosannah Williams'
	liv_member_data$Person[liv_member_data$Person == 'Andrew Hector'] <- 'Andy Hector'
	liv_member_data$Person[liv_member_data$Person == 'Chua Wan JI'] <- 'Chua Wan Ji'
	liv_member_data$Person[liv_member_data$Person == 'IKA RAFIKA BINTI CHAMIM ACHMADI'] <- 'Ika Rafika Binti Chamim Achmadi'
	liv_user_data$FirstName[liv_user_data$FirstName == 'IKA RAFIKA BINTI CHAMIM'] <- 'Ika Rafika Binti Chamim'
	liv_user_data$LastName[liv_user_data$LastName == 'ACHMADI'] <- 'Achmadi'
	
	# get rid of middle initials
	liv_member_data$Person <- gsub(' [A-Z.]+ ', ' ', liv_member_data$Person)
	
	# drop some bad membesrship rows
	liv_member_data <- liv_member_data[-which(liv_member_data$Project == 'SAFE-PRJ-51'),]
	liv_member_data <- liv_member_data[-which(liv_member_data$Person == 'ETH Zurich'),]
	
	# missing membership
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-63', 'Anthony Turner', 'PhD Student'))
	
	# now all of Liv's members appear in her user list and vice versa
	liv_user_data$Person <- with(liv_user_data, paste(FirstName, LastName))
	check <- merge(liv_user_data, liv_member_data, by='Person', all=TRUE)
	
	# no projects
	check[is.na(check$Project),]
	
	# no user data
	check[is.na(check$FirstName),]
	
	# match the role set to the DB plan
	# project_roles = ['Lead Researcher', 'Supervisor', 'Co-supervisor', 'PhD Student', 
	                 # 'MSc Student', 'Undergraduate', 'PI', 'Co-I', 'Post Doc', 
	                 # 'Field Assistant', 'Malaysian Collaborator']
	library(car)
	
	reclass <- "c('collaborator', 'Collaborator') = 'Collaborator';
				c('post doc', 'Post Doc') = 'Post Doc';               
				c('supervisor', 'advisor') = 'Supervisor';
				c('Malaysian Collaborator', 'Malaysian collaborator', 'local collaborator') = 'Malaysian Collaborator';
				c('PhD Student', 'PhD student') = 'PhD Student';
				c('lead researcher') = 'Lead Researcher';"
	
	liv_member_data$Position <- recode(liv_member_data$Position, reclass)
	
	unique(liv_member_data$Position)
	
	# check against info from the web
	web_user_data <- read.csv('Users_table.csv', stringsAsFactors=FALSE)
	
	# sanitise and  get rid of middle initials
	web_user_data$first_name <- sanitise(web_user_data$first_name)
	web_user_data$last_name <- sanitise(web_user_data$last_name)
	
	web_user_data$first_name <- gsub(' [A-Z].?$', '', web_user_data$first_name)
	
	
	# reconciling
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-19', 'Louise Ashton', 'Post Doc'))
	liv_user_data <- rbind(liv_user_data, list('Louise','Ashton', 'Natural History Museum', NA,'Louise Ashton'))
	
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-19', 'Hannah Griffiths', 'Supervisor'))
	liv_user_data <- rbind(liv_user_data, list('Hannah', 'Griffiths', 'Liverpool University', NA,'Hannah Griffiths'))
	
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-45', 'Jon Knight', 'Supervisor'))
	liv_user_data <- rbind(liv_user_data, list('Jon', 'Knight', 'Imperial College London', NA,'Jon Knight'))
	
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-45', 'Megan Quinlan', 'Collaborator'))
	liv_user_data <- rbind(liv_user_data, list('Megan', 'Quinlan', 'Imperial College London', NA,'Megan Quinlan'))
	
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-36', 'Anne Seltmann', 'PhD Student'))
	liv_user_data <- rbind(liv_user_data, list('Anne', 'Seltmann', 'Institute for Zoological and Wildlife Research', NA,'Anne Seltmann'))

	liv_user_data <- rbind(liv_user_data, list('Daisy', 'Dent', 'University of Stirling', 'daisy.h.dent@gmail.com','Daisy Dent'))
	liv_member_data <- rbind(liv_member_data, list('SAFE-WEB-1', 'Daisy Dent', 'Lead Researcher'))

	liv_member_data <- rbind(liv_member_data, list('SAFE-WEB-2', 'Mohammad Imran Ebrahim', 'Lead Researcher'))

	# non project key people
	liv_user_data <- rbind(liv_user_data, list('Laura', 'Kruitbos', 'Aberdeen University', 'l.kruitbos@abdn.ac.uk','Laura Kruitbos'))
	liv_user_data <- rbind(liv_user_data, list('David', 'Orme', 'Imperial College London', 'd.orme@imperial.ac.uk','David Orme'))
	liv_user_data <- rbind(liv_user_data, list('Olivia', 'Daniel', 'Imperial College London', 'olivia.daniel08@imperial.ac.uk','Olivia Daniel'))
	
	# people with outputs but no projects
	liv_user_data <- rbind(liv_user_data, list('Holly', 'Harrison',  'University of Bristol', NA, 'Holly Harrison'))
	liv_user_data <- rbind(liv_user_data, list('Leah', 'Trigg', 'Imperial College London', NA, 'Leah Trigg'))
	liv_user_data <- rbind(liv_user_data, list( "Stephanie", "Sammann", "Imperial College London", NA, "Stephanie Sammann"))
	liv_user_data <- rbind(liv_user_data, list( "Thomas", "Bell", "Imperial College London", NA, "Thomas Bell"))
	liv_user_data <- rbind(liv_user_data, list( "Nick", "Haddad", "North Carolina State University", "nick_haddad@ncsu.edu", "Nick Haddad"))
	liv_user_data <- rbind(liv_user_data, list( "Michael", "Senior", "University of York", "mjms501@york.ac.uk", "Michael Senior"))
	liv_user_data <- rbind(liv_user_data, list( "Joshua", "March", "Imperial College London", NA, "Joshua March"))
	liv_user_data <- rbind(liv_user_data, list( "Jon", "Hamley", "Imperial College London", NA, "Jon Hamley"))




	
	# name mismatches (mostly surname split)
	web_user_data$first_name[web_user_data$first_name == 'Esther Lonnie'] <- 'Esther'
	web_user_data$last_name[web_user_data$last_name == 'Baking'] <- 'Lonnie Baking'
	
	web_user_data$first_name[web_user_data$first_name == 'Mahadimenakbar Mohamed'] <- 'Mahadimenakbar'
	web_user_data$last_name[web_user_data$last_name == 'Dawood'] <- 'Mohamed Dawood'
	
	web_user_data$first_name[web_user_data$first_name == 'Katharine J.M'] <- 'Katharine'
	
	web_user_data$first_name[web_user_data$first_name == 'Mohammad Imran bin'] <- 'Mohammad'
	web_user_data$last_name[web_user_data$last_name == 'Ebrahim'] <- 'Imran Ebrahim'
	
	web_user_data$first_name[web_user_data$last_name == 'Ewers'] <- 'Robert'
	
	web_user_data$first_name[web_user_data$first_name == 'Arman Hadi Mohammad'] <- 'Arman'
	web_user_data$last_name[web_user_data$last_name == 'Fikri'] <- 'Hadi Fikri'
	
	web_user_data$first_name[web_user_data$first_name == 'Kueh Boon'] <- 'Kueh'
	web_user_data$last_name[web_user_data$last_name == 'Hee'] <- 'Boon Hee'
	
	web_user_data$first_name[web_user_data$first_name == 'Chua Wan'] <- 'Chua'
	web_user_data$last_name[web_user_data$last_name == 'Ji'] <- 'Wan Ji'
	
	web_user_data$first_name[web_user_data$first_name == 'Chey Vun'] <- 'Chey'
	web_user_data$last_name[web_user_data$last_name == 'Khen'] <- 'Vun Khen'
	
	web_user_data$first_name[web_user_data$first_name == 'Suzila Binti'] <- 'Suzila'
	web_user_data$last_name[web_user_data$last_name == 'Kilipus'] <- 'Binti Kilipus'
	
	web_user_data$first_name[web_user_data$first_name == 'Ulrich'] <- 'Ully'
	
	web_user_data$first_name[web_user_data$first_name == 'Melissa Melody'] <- 'Melissa'
	web_user_data$last_name[web_user_data$last_name == 'Leduning'] <- 'Melody Leduning'
	
	web_user_data$first_name[web_user_data$first_name == 'Nursuhadila Binti'] <- 'Nursuhadila'
	web_user_data$last_name[web_user_data$last_name == 'Mahmud'] <- 'Binti Mahmud'
	
	web_user_data$first_name[web_user_data$first_name == 'Mohd Nurazmeel Bin'] <- 'Mohd Nurazmeel'
	web_user_data$last_name[web_user_data$last_name == 'Mokhtar'] <- 'Bin Mokhtar'
	
	web_user_data$first_name[web_user_data$first_name == 'Musa bin'] <- 'Musa'
	web_user_data$last_name[web_user_data$last_name == 'Muchtar'] <- 'bin Muchtar'
	
	web_user_data$first_name[web_user_data$first_name == 'Hisahsi'] <- 'Hisashi'
	
	web_user_data$last_name[web_user_data$last_name == 'Ruiz-Gutierrez'] <- 'Ruiz‐Gutierrez'

	web_user_data$first_name[web_user_data$first_name == 'Jaya Seelan Sathiya'] <- 'Jaya'
	web_user_data$last_name[web_user_data$last_name == 'Seelan'] <- 'Seelan Sathiya Seelan' 

	web_user_data$first_name[web_user_data$first_name == 'Isolde Lane'] <- 'Isolde'
	web_user_data$last_name[web_user_data$last_name == 'Shaw'] <- 'Lane Shaw' 

	web_user_data$first_name[web_user_data$first_name == 'Khoo Min'] <- 'Khoo'
	web_user_data$last_name[web_user_data$last_name == 'Sheng'] <- 'Min Sheng' 

	web_user_data$first_name[web_user_data$first_name == 'Waidi Bin'] <- 'Waidi'
	web_user_data$last_name[web_user_data$last_name == 'Sinun'] <- 'Bin Sinun' 

	web_user_data$first_name[web_user_data$first_name == 'Hamzah Bin'] <- 'Hamzah'
	web_user_data$last_name[web_user_data$last_name == 'Tangki'] <- 'Bin Tangki' 

	web_user_data$first_name[web_user_data$first_name == 'Yit Arn'] <- 'Yit'
	web_user_data$last_name[web_user_data$last_name == 'Teh'] <- 'Arn Teh' 

	web_user_data$first_name[web_user_data$first_name == 'Wendy Yanling'] <- 'Wendy'
	web_user_data$last_name[web_user_data$last_name == 'Wang'] <- 'Yanling Wang' 

	web_user_data$first_name[web_user_data$first_name == 'Bakhtiar Effendi'] <- 'Bakhtiar'
	web_user_data$last_name[web_user_data$last_name == 'Yahya'] <- 'Effendi Yahya' 
	
	web_user_data$first_name[web_user_data$first_name == 'Kalsum Mohd'] <- 'Kalsum'
	web_user_data$last_name[web_user_data$last_name == 'Yusah'] <- 'Mohd. Yusah' 

	row <- which(web_user_data$first_name == 'Norzakiah Binti')
	web_user_data$first_name[row] <- 'Norzakiah'
	web_user_data$last_name[row] <- 'Binti Zakaria'

	row <- which(web_user_data$last_name == 'Zakaria')
	web_user_data$first_name[row] <- 'Mohd'
	web_user_data$last_name[row] <- 'Afif Zakaria'

	row <- which(web_user_data$first_name == 'Robert J. Fletcher')
	web_user_data$first_name[row] <- 'Robert'
	web_user_data$last_name[row] <- 'Fletcher, Jr'


	# dear god that was tedious, but no remaining issues
	user_merge <- merge(liv_user_data, web_user_data, 
						by.x=c('LastName', 'FirstName'),
	                    by.y=c('last_name', 'first_name'),  all=TRUE)
	
	user_merge[is.na(user_merge$Person),]	

	# add the legacy_user_id to do cross matching on DB load.
	liv_user_data$legacy_user_id <- seq_along(liv_user_data$LastName)
	
# TAGS

	liv_tag_wb <- loadWorkbook('liv_data_files/ProjectTags.xlsx')
	liv_tag_data <- readWorksheet(liv_tag_wb, 1)
	
	setdiff(liv_tag_data$Project.Code, projects$Code)	
	setdiff(projects$Code,liv_tag_data$Project.Code)	

	# turn into tag sets
	liv_tag_names <- names(liv_tag_data)[3:18]
	liv_tag_names <- gsub('\\.', ' ', liv_tag_names)
	
	bin <- as.matrix(liv_tag_data[,3:18])
	tag_list <- apply(bin, 1, function(x) liv_tag_names[as.logical(x)])	
	names(tag_list) <- liv_tag_data$Project.Code
	
	# add the two web ones
	tag_list[['SAFE-WEB-1']] <- c('Plant Science', 'Ecology')
	tag_list[['SAFE-WEB-2']] <- c("Biodiversity", "Zoology", "Infectious Diseases")
	
	# add research tags to projects - web2py uses pipe delimited text
	tag_list_inserts <- sapply(tag_list, function(x) paste('|', paste( x, collapse='|'), '|', sep=''))
	
	tags <- data.frame(project = names(tag_list),
					   tags = tag_list_inserts)	
	projects <- merge(projects, tags, by.x='Code', by.y='project')
	
	str(projects)

# PROJECT COORDINATORS

	# do all projects have a lead researcher - nope. not even close.
	# so match in contact_emails to assign coordinators
	leads <- subset(liv_member_data, Position == 'Lead Researcher')
	length(leads) # 66...
	
	# do all projects have members?
	# - correct typo in project codes and drop two projects
	liv_member_data$Project <- gsub('PJR','PRJ', liv_member_data$Project)
	liv_member_data <- liv_member_data[! liv_member_data$Project %in% c("SAFE-PRJ-17","SAFE-PRJ-49"),]
	
	projects_with_members <- unique(liv_member_data$Project)
	length(projects_with_members)

	setdiff(projects$Code, projects_with_members)
	setdiff(projects_with_members, projects$Code)
	
	# do all contact emails appear in the user table?
	setdiff(projects$contact_email, liv_user_data$Email)
	setdiff(liv_project_data$ContactEmail, liv_user_data$Email)
	
	# oh _for fuck's sake_. <Throws toys out of cot, burns cot down>
	(no_match <- setdiff(projects$contact_email, liv_user_data$Email))

	# fix straight errors
	liv_user_data$Email[liv_user_data$Email == 's.morris14@ic.a.cuk'] <- "s.morris14@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$Email == 'c.phipps13@imperial.ac.uk;'] <- "c.phipps13@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$Email == 'clare.wilkinson12@imperial.ac.uk;'] <- "clare.wilkinson12@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$Email == "R.P.D.Walsh@Swansea.ac.uk"] <- "r.p.d.walsh@swansea.ac.uk"
	
	projects$contact_email[projects$contact_email == 'm.j.struebig@kent.ac.yk'] <- "m.j.struebig@kent.ac.uk"
	projects$contact_email[projects$contact_email == 'kem36@kent.ac.uk;m.j.struebig@kent.ac.uk'] <- "kem36@kent.ac.uk"
	projects$contact_email[projects$contact_email == 'hbtiandun@yahoo.com'] <- "hbtiandun@gmail.com"
	projects$contact_email[projects$contact_email == "mattstruebig@gmail.com"] <- "m.j.struebig@kent.ac.uk"
		
	# copy the others into the alt email field
	liv_user_data$alt_email <- liv_user_data$Email
	liv_user_data$Email[liv_user_data$LastName == 'Higton'] <- 's.a.higton.798104@swansea.ac.uk'
	liv_user_data$Email[liv_user_data$LastName == 'Pfeifer'] <- "m.pfeifer@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Yanling Wang'] <- "wyw24@cam.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Cusack'] <- "jeremy.cusack09@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Sayer'] <- "e.sayer@lancaster.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Singh'] <- 	"jojo.singh@st-hildas.ox.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Loveridge'] <- "robin.loveridge11@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Gleave'] <- "rosalind.gleave12@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Fitzmaurice'] <- 	"amy.fitzmaurice13@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Deere'] <- "nicolas.deere@gmail.com"
	liv_user_data$Email[liv_user_data$LastName == 'Bin Tangki'] <- "hamzah.tangki@uzh.ch"
	liv_user_data$Email[liv_user_data$LastName == 'Bishop'] <- 	"thomasrhys.bishop@gmail.com"
	liv_user_data$Email[liv_user_data$LastName == 'Brant'] <- "hayley.brant10@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Psomas'] <- "e.psomas14@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Nainar'] <- "anand.destiny@yahoo.com"
	liv_user_data$alt_email[liv_user_data$LastName == 'Struebig'] <- "mattstruebig@gmail.com"
	liv_user_data$Email[liv_user_data$LastName == 'Bernard'] <- "hbtiandun@gmail.com"
	liv_user_data$Email[liv_user_data$LastName == 'Wearn'] <- "oliver.wearn08@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$Email == "claudiagray@gmail.com"] <- "claudia.gray@zoo.ox.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Massam'] <- "michael.massam11@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Plowman'] <- "nichola.plowman11@imperial.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Fayle'] <-  "tmf26@cam.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Giles'] <-  "eg249@kent.ac.uk"
	liv_user_data$Email[liv_user_data$LastName == 'Afif Zakaria'] <-  "afif.maz@gmail.com"

	# OK - now done
	(no_match <- setdiff(projects$contact_email, liv_user_data$Email))
	
	# blank out alt_emails that aren't used
	liv_user_data$alt_email[liv_user_data$alt_email == liv_user_data$Email] <- ''
	
	# Right, now we have a contact email mapped for each project, so does that equate
	# to a member of each project? Which is a three way merge.

	# a few people listed as contacts aren't on the project members lists
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-1', 'Robert Ewers', 'Lead Researcher'))
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-2', 'Laura Kruitbos', 'Coordinator'))
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-123', 'Laura Kruitbos', 'Coordinator'))
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-84', 'Laura Kruitbos', 'Coordinator'))
	liv_member_data <- rbind(liv_member_data, list('SAFE-PRJ-44', 'Edgar Turner', 'Lead Researcher'))

	# - first, do all project members appear in the user db
	user_merge <- merge(liv_user_data, liv_member_data, by='Person', all=TRUE) 
	
	# these aren't a problem, people who aren't in a project
	user_merge[which(is.na(user_merge$Position)), ]
	
	# and there aren't any people in the members list missing from the user DB
	user_merge[which(is.na(user_merge$LastName)), ]
		
	# now all contact emails by project match up to at a project record
	project_coords <- subset(projects, select=c(Code, contact_email))
	project_coords$coord <- TRUE
	
	# Match coordinators into the member db
	members <- merge(user_merge, project_coords, by.x=c('Project', 'Email'),
						  by.y=c('Code','contact_email'), all=TRUE)

	# no missing rows
	members[is.na(members$Person),]
	
	# set coordinator = FALSE for non-coordinators 
	members$coord <- ifelse(is.na(members$coord), FALSE, TRUE)

# OUTPUTS

	# get the outputs
	outputs <- read.csv('output_inputs_with_users.csv', stringsAsFactors=FALSE)
	
	# do all the hand edited output owners match up
	test <-merge(liv_user_data, outputs) 
	any(is.na(test$legacy_user_id))
	
	# validate the formats
	unique(outputs$format)
	outputs$format[outputs$format == 'Journal'] <- 'Journal Paper'
	outputs$format[outputs$format == 'Chapters'] <- 'Book Chapter'
	outputs$format[outputs$legacy_output_id == 16] <- 'Report'
	outputs$format[outputs$legacy_output_id == 54] <- 'Website'
	outputs$format[outputs$legacy_output_id == 55] <- 'Field Guide'
	outputs$format[outputs$legacy_output_id == 56] <- 'Field Guide'
	
	
	# match up projects to outputs	
	project_outputs <- read.csv('project_outputs_inputs.csv')
	# this file uses the old legacy_project_id codes, which have been replaced by Liv's text names,
	# so we need to sub those in and add the owner
	project_outputs_new <- merge(project_outputs, projects, by='legacy_project_id')
	project_outputs_new <- merge(project_outputs_new, outputs, by='legacy_output_id')

# FINALLY MERGE THE UPDATED CONTACT LIST INTO THE USERS

	contacts <- read.csv('db_safe_contacts.csv', stringsAsFactors=FALSE)
	mail_match <- match(contacts$email, liv_user_data$Email)
	name_match <- match(contacts$last_name, liv_user_data$LastName)
	matches <- ifelse(is.na(mail_match), ifelse(is.na(name_match), NA, name_match), mail_match)

	# ryan gray is not claudia gray  - all other look ok.
	matches[3] <- NA
	combine <- cbind(contacts, liv_user_data[matches,])
	combine[, c('first_name','last_name', 'FirstName','LastName', 'legacy_user_id')]


	# match up names and insert new fields from contacts
	liv_user_data$Person <- NULL
	names(liv_user_data) <- c('first_name','last_name','institution','email', 'legacy_user_id', 'alt_email')
	contacts$legacy_user_id <- liv_user_data$legacy_user_id[matches]
	liv_user_data <- merge(contacts, liv_user_data, by='legacy_user_id', all=TRUE)

	# combine fields
	cb_fld <- function(x,y){
		x <- ifelse(x == '', NA, x)
		y <- ifelse(y == '', NA, y)
		ret <- ifelse(is.na(x), ifelse(is.na(y), NA, y), x)
		return(ret)
	}
	
	final_user_data <- with(liv_user_data, 
							data.frame(title = title,
									   first_name = cb_fld(first_name.x, first_name.y),
									   last_name = cb_fld(last_name.x, last_name.y),
									   institution = cb_fld(institution.x, institution.y),
									   email = cb_fld(email.x, email.y),
									   alt_email = alt_email,
									   website = website,
									   taxonomic_expertise = taxonomic_expertise,
									   thumbnail_picture = thumbnail_picture,
									   legacy_user_id  = legacy_user_id,
									   contacts_group  = contacts_group,
									   contacts_role = contacts_role))
	
	contacts_data <- final_user_data[,c('legacy_user_id','contacts_group','contacts_role')]
	contacts_data <- na.omit(contacts_data)
	
	final_user_data <- subset(final_user_data, select= -11:-12)
	
	
# OK - put together the final DB inserts

	write.csv(projects, file='final_projects.csv', row.names=FALSE)
	write.csv(final_user_data, file='final_users.csv', row.names=FALSE, na='')
	write.csv(contacts_data, file='final_contacts.csv', row.names=FALSE, na='')
	members <- subset(members, select=c(Project, legacy_user_id, Position, coord))
	write.csv(members, file='final_project_members.csv', row.names=FALSE)
	write.csv(outputs, file='final_outputs.csv', row.names=FALSE)
	project_outputs_new <- subset(project_outputs_new, select=c(Code, legacy_output_id, legacy_user_id))	
	write.csv(project_outputs_new, file='final_project_outputs.csv', row.names=FALSE)

	
	