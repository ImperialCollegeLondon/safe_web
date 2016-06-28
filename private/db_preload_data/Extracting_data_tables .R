library(RCurl)
library(XML)
library(jpeg)

setwd("/Users/dorme/Research/SAFE/SAFE_website_plan/wget_existing_website/www.safeproject.net")

output_folder <- '/Users/dorme/Research/SAFE/Web2Py/web2py/applications/SAFE_Web/private/db_preload_data'

##----------------------------------------------
## Useful functions
##----------------------------------------------

	# remove trailing and leading spaces and filter out some random non printing characters
	scrubCrap <- function(str, aloud=TRUE){
		
		# look for line endings, carriage returns, NBSP (Unicode C2 A0) at either end
		# - can't find a way to simply insert this - \uC2A0 seems like it should work.
		nbsp <- rawToChar(as.raw(c(0xc2, 0xa0)))
	
		re <- paste('^[ ',nbsp,'\n\r]+|[ ',nbsp,'\n\r]+$', sep='')
		str_chomp <- gsub(re, '', str)
		
		# replace internal NBSPs
		str_clean <- gsub(nbsp, ' ', str_chomp)
		
		# look for internal random control characters
		str_clean <- gsub('[\u0090\u009d]', '', str_clean)
		
		# remove 'fancy' text element	
		str_clean <- gsub("‘|’", "'", str_clean)
		str_clean <- gsub("–", "-", str_clean)
	
		return(str_clean)
		
	}
	
	# extract patterns from strings - doesn't handle multiple matches
	extract_re <- function(pattern, x, ignoreNA=TRUE){
		 r <- regexpr(pattern, x)
		out <- rep(NA,length(x))
		ind <- r != -1
		if(ignoreNA) ind <- ind & ! is.na(x) 
		out[ind] <- regmatches(x, r)
		return(out)
	}

################################################
## PROJECTS
################################################

{	
	##----------------------------------------------
	## Extracting project database from local copy of original website scraped with wget
	##----------------------------------------------
	
	# load in the project list page
	projectListPage <- 'science/ecological-monitoring/index.html?id=5.html'
	
	# parse the html to make it easier to extract
	projects <- htmlTreeParse(projectListPage, useInternalNodes=TRUE)
	
	# single table with projects as rows, so target the rows
	# using XPath expressions (syntax copied from SelectorGadget)
	xp_expr <- '//*[contains(concat( " ", @class, " " ), concat( " ", "projectfile-row", " " ))]'
	nodes <- getNodeSet(projects, xp_expr)
	
	
	##----------------------------------------------
	## Also need to look at the contents of the project directory directly
	## as there are broken links in the main table
	##----------------------------------------------
	
	local_projects_dir <- 'projects'
	local <- dir(local_projects_dir, pattern='index.html', recursive=TRUE, full=TRUE)
	
	# this includes html files for comment feeds, which we'll discard for now
	local <- local[! grepl('/feed/', local)]
	
	# the folder also contains outputs that are stored in the project area,
	# so catch those and expunge them from the list for now
	is_output <-  logical(length=length(local))
	
	for(i in seq_along(local)){
		
		details <- htmlTreeParse(file=local[i], useInternalNodes=TRUE)
		
		# test to see if this is an output that is lurking in the projects page
		xp_expr <- '//*[contains(concat( " ", @class, " " ), concat( " ", "category-output", " " ))]'
		contains_output <- xpathSApply(details, xp_expr) 
		
		if(length(contains_output) > 0) is_output[i] <- TRUE
	}
	
	local <- local[! is_output]
	
	## 1 more project in the scraped project folder
	## than in the web project list. Fix this.
	length(nodes)
	length(local)
	
	##----------------------------------------------
	## Get the images and titles from the main list page
	##----------------------------------------------
	
	project_links_table <- data.frame(id=integer(),
								 	  img_file = character(),
								 	  title = character(),
	 	  							  stringsAsFactors=FALSE)				
	
	for(i in seq_along(nodes)){
		
		# extract image from node
		#image source
		img_src <- xpathSApply(nodes[[i]], './/img', xmlGetAttr, 'src')
		
		# get title and href of main page
		title <- xpathSApply(nodes[[i]], '.',  'xmlValue')
		
		project_links_table[i,] <- list(i, img_src, scrubCrap(title))
	
	}
	
	##----------------------------------------------
	## Now get the details and the outputs from the
	## underlying project pages 
	##----------------------------------------------
	
	# db table 
	projects_table <- data.frame(id=integer(),
								 n_tables = integer(),
								 n_rows = integer(),
								 n_outputs = integer(),
								 title=character(),
								 researchers=character(),
								 contact_email=character(),
								 project_home_country=character(),
								 institution=character(),
								 resources=character(),
								 sampling_scales=character(),
								 sampling_sites=character(),
								 time_frame=character(),
								 methods=character(),
								 rationale=character(),
								 stringsAsFactors=FALSE)
	
	# output table and a counter to track rows added (One to Many)
	outputs_from_projects <- data.frame(project_id=integer(),
								 img_src=character(),
								 page_link=character(),
								 title=character(),
								 stringsAsFactors=FALSE)
	j <- 1
	
	for(i in seq_along(local)){
		
		details <- htmlTreeParse(local[i], useInternalNodes=TRUE)
		
		# one problem here is the missing image from the list page - not linked here
		
		# Pages contain three components we are intersted in:
		# A) get the title
		xp_expr <- '//*[contains(concat( " ", @class, " " ), concat( " ", "h1title", " " ))]'
		title <- scrubCrap(xpathSApply(details, xp_expr, xmlValue))
	
		# B) get the table of project details - actually a table containing sub tables
		xp_expr <- '//table'
		tables <- xpathSApply(details, xp_expr)
	
		# C) A list of any linked outputs 
		xp_expr <- '//*[(@id = "endcontent_output_list")]'
		outputs <- xpathSApply(details, xp_expr)
	
		# fill in parsing details
	 	projects_table[i, 1:4] <- list(i, length(tables), length(data), length(outputs))
	
		# Now parse the content out of (B) and (C)
		# - ideally we'd make use of the page structure but it is very inconsistent 
		#   with highly variable numbers of tables nested subtables and rows (see output summary table)
		
		# - grab table rows regardless of nesting in subtables and
		#   look physically for indices, not rely on order	
		data <- 	unlist(xpathApply(details, '//tr', 'xmlValue'))
	
		# handle a handful of pages with duplicated tables (10 tables)
		if(length(data) == 36) data <- data[1:18]
	
		# - look for various components
		# - first, scrub crap off the contents
		data <- scrubCrap(data)
		
		# rows with two columns
		patterns <- c('^Researchers:\n', '^Email:\n', '^Nationality:\n',
					  '^Institution:\n', '^Resources:\n', '^Spatial Scale:\n',
					  '^Sampling Sites:\n', '^Time Frame:\n')
		twocol_vals <- character(8)
	
		for(pt in seq_along(patterns)){
			ind <- grep(patterns[pt], data)
			if(length(ind) > 0){
				twocol_vals[pt] <- gsub(patterns[pt], "", data[ind]) 
			} 
		}
	
		# rows with single merged column and header on previous row
		patterns <- c('^Rationale and questions$', '^Methods$')
		onecol_vals <- character(2)
	
		for(pt in seq_along(patterns)){
			ind <- grep(patterns[pt], data)
			if(length(ind) > 0){
				onecol_vals[pt] <- gsub(patterns[pt], "", data[ind + 1]) 
			} 
		}
		
		projects_table[i, 5:15] <-  as.list(c(title, twocol_vals, onecol_vals))
		
		# Now handle output links, which are in an html list
		if(length(outputs) == 1){
	
			output_list <- xpathApply(outputs[[1]], './/li')
			
			for(nd in output_list){
				output_links <- xpathSApply(nd, path='.//a', fun=xmlGetAttr, 'href')
				output_content <- xpathSApply(nd, path='.//a', xmlValue)
				output_img <-   xpathSApply(nd, path='.//img', fun=xmlGetAttr, 'src')
				
				details <- list(project_id=i, img_src=output_img, page_link=output_links[3], 
								title=scrubCrap(output_content[2]))
				outputs_from_projects[j, ] <- details
				j <- j + 1
			}
		} else if(length(outputs) == 2) {
			stop('Unexpected item in the outputs area')
		}
	}
	
	# Sheesh. How many bloody layout structures?
	unique(projects_table[,2:3])
	
	# check for any nonprinting characters (other than new line)
	unique(as.vector(sapply(projects_table[,5:15], extract_re, pattern='[^[:print:]]')))
	
	# parse the start and end dates
	times <- strsplit(projects_table$time, ' until | – ')
	
	start <- sapply(times, '[', 1)
	end <- sapply(times, '[', 2)
	
	start_dmy <- as.Date(start, format='%d %B %Y')
	start_my <-  as.Date(paste('1',start), format='%d %B %Y')
	start_y <-   as.Date(paste('1 Jan',start), format='%d %B %Y')
	
	start_dmy <- ifelse(is.na(start_dmy), start_my, start_dmy)
	projects_table$start_date <- as.Date(ifelse(is.na(start_dmy), start_y, start_dmy), origin = "1970-01-01")
	
	
	end_dmy <- as.Date(end, format='%d %B %Y')
	end_my <-  as.Date(paste('1',end), format='%d %B %Y')
	end_y <-   as.Date(paste('1 Jan',end), format='%d %B %Y')
	
	end_dmy <- ifelse(is.na(end_dmy), end_my, end_dmy)
	projects_table$end_date <- as.Date(ifelse(is.na(end_dmy), end_y, end_dmy), origin = "1970-01-01")
	
	# missing values
	projects_table$end_date[is.na(projects_table$end_date)] <- as.Date('2020-1-1')
	
	##----------------------------------------------
	## Now match the images and details together
	##----------------------------------------------
	
	# remove fancy hyphens and quotes from titles
	project_links_table$title <- scrubCrap(project_links_table$title)
	projects_table$title <- scrubCrap(projects_table$title)
	
	
	# strip out the ID from the links table - stick to one!
	project_links_table$id <- NULL
	projects <- merge(project_links_table, projects_table, all=TRUE)
	nrow(projects) == nrow(projects_table)
}

################################################
## OUTPUTS
################################################
	
	## Great now to handle the matching outputs
	## - need to check those listed with a project against those
	#    in the outputs table
	
	# parse the html of the page to make it easier to extract
	
	outputs_list_page <- 'index.html?p=320.html'
	outputs <- htmlTreeParse(outputs_list_page, useInternalNodes=TRUE)
	
	# single table with projects as rows, so target the rows
	# using XPath expressions (syntax copied from SelectorGadget)
	xp_expr <- '//*[contains(concat( " ", @class, " " ), concat( " ", "outputfile-row", " " ))]'
	nodes <- getNodeSet(outputs, xp_expr)
	
	# not all outputs have a link to a project
	length(nodes)
	nrow(outputs_from_projects)
	
	# need image (not all have them), title, format and download link 
	# from summary table and description from the linked page
	
	# db table 
	output_table <- data.frame(id = integer(),
							   picture=character(),
							   file=character(),
							   title=character(),
							   page_link=character(),
							   format=character(),
							   n_paras=integer(),
							   stringsAsFactors=FALSE)
	
	output_content_list <- list()
	
	for(i in seq_along(nodes)){
		
		#image source
		img_src <- xpathSApply(nodes[[i]], './/img', xmlGetAttr, 'src')
		
		# href of dsecription page and output file
		hrefs <- xpathSApply(nodes[[i]], './/a', xmlGetAttr, 'href')
		
		# get format and title
		alltext <- xpathSApply(nodes[[i]], '.',  'xmlValue')
		alltext <- gsub('Click here to download', '', alltext)
		alltext <- strsplit(alltext, split='Format: ')[[1]]
		title <- scrubCrap(alltext[1])
		format <- alltext[2]
		
		# not all outputs have local file links (journal links)
		if(length(hrefs) == 1){
			details_url <- hrefs[1]
			file_name <- NA
		} else if(length(hrefs) == 3){
			details_url <- hrefs[2]
			file_name <- hrefs[3]
		}
	
		output_table[i, 1:6] <- list(i, img_src, file_name, title, details_url, format)
	
		# check there is a resolved link to a local file
		filename <- sub('%3F','?',details_url)
		if(! file.exists(filename)){
			output_table[i, 7] <- NA
			output_content_list[[i]] <- NA
		} else {
	
			#load details page (swapping html ? back in)
			details <- htmlTreeParse(file=filename, useInternalNodes=TRUE)
		
			# check the title
			xp_expr <- '//*[contains(concat( " ", @class, " " ), concat( " ", "h1title", " " ))]'
			title_alt <- scrubCrap(xpathSApply(details, xp_expr, xmlValue))
		
			if(! title == title_alt) cat('\n', title, '\n', title_alt, '\n')
		
			# get the entry content and break down into paragraphs
			xp_expr <- '//*[(@id = "entry-content")]'
			contentNode <- xpathSApply(details, xp_expr)[[1]]
			xp_expr <- './/p'	
			content_paras <- scrubCrap(xpathSApply(contentNode, xp_expr, xmlValue))
		
			# Unpack that
			# - trim off download
			dwn <- which(content_paras == "Output File: Download")
			if(length(dwn) > 0) content_paras <- content_paras[-dwn]
		
			# - remove output type
			typ <- which(grepl('Output Format:', content_paras))
			if(length(typ) > 0) content_paras <- content_paras[-typ]
	
			output_table[i,7] <- length(content_paras)
			output_content_list[[i]] <- content_paras
			
		}
	}
	
	# look for bits of information in the confusion that is the rest of the content.
	
	# function to extract lines matching patterns
	content_chunks <- function(lst, pattern){
		
		chnks <- sapply(lst, grep, pattern=pattern)
		chnks <- mapply('[', lst, chnks)
		names(chnks) <- seq_along(chnks)
		chnks <- chnks[sapply(chnks, function(x) length(x) > 0)]
		
		return(chnks)
	}
	
	# function to extract content and return it along with a list of paras to drop
	extract_and_index <- function(lst, pattern){
	
		txt <- character(length(lst))
		ind <- integer(length(lst))
	
		for(i in seq_along(lst)){
			r <- regexpr(pattern=pattern, text=lst[[i]])
			
			if(length(r) > 0 & all(! is.na(r))){
				if(all(r == -1)){
					txt[i] <- NA
				} else if(sum(r > 0) ==1){
					txt[i] <- regmatches(lst[[i]], r)
					ind[i] <- which(r > 0)
				} else {
					stop('multiple matches for pattern')
				}
			} else {
				txt[i] <- NA
			}		
		}
	
		return(list(txt=txt, ind=ind))
	}	
	
	# create a copy of the content list and modify it, extracting info along the way
	# - strip out any paragraph that contains only white space or only the words abstract/summary etc.
	in_process <- lapply(output_content_list, function(x){bad <- grep('^$|^[[:space:]]$|^Abstract[:.]?$|^ABSTRACT:?$|^Highlights$|^Summary:?$', x)
												   if(length(bad) > 0) x[- bad] else x})
	
	# Look for patterns of content
	
	# A) DOI and email in the same chunks so do together
	pattern = 'http://dx.doi.org[-A-z0-9/.]+|doi: [-A-z0-9/.]+'
	content_chunks(in_process, pattern=pattern)
	doi <- extract_and_index(in_process, pattern=pattern)
	
	output_table$doi <- doi$txt
	
	# B) Contact email
	pattern = '[a-z0-9.]+@[a-z0-9.]+'
	content_chunks(in_process, pattern=pattern)
	email <- extract_and_index(in_process, pattern=pattern)
	
	output_table$contact_email <- email$txt
	
	# A+B) drop paragraphs matching DOI and emails
	for(i in seq_along(in_process)){
		
		ind <- c(email$ind[i], doi$ind[i])
		ind <- ind[ind > 0]	
		if(length(ind) > 0) in_process[[i]] <- in_process[[i]][-unique(ind)]
	}
	
	# C) Other URLs
	pattern = 'http://[-A-z0-9/.]+'
	content_chunks(in_process, pattern=pattern)
	url <- extract_and_index(in_process, pattern=pattern)
	
	output_table$url <- url$txt
	
	# drop indices
	for(i in seq_along(in_process)){
		
		ind <- url$ind[i]
		ind <- ind[ind > 0]	
		if(length(ind) > 0) in_process[[i]] <- in_process[[i]][-ind]
	}
		
	# D) A citation like field - check for only a single para with 20XX in it?
	pattern <- '20[0-9]{2}'
	year_chunks <- content_chunks(in_process, pattern=pattern)
	year <- extract_and_index(in_process, pattern=pattern)
	
	# needs a minor tweak (one description contains a reference to 2010)
	year$ind[56] <- 0
	
	# extract the whole of those paragraphs
	output_table$year_para <- mapply(function(i,j) {xx <- in_process[[i]][j]
		  											if(length(xx) > 0) xx else NA},
		  							 seq_along(year$ind), year$ind)
		  							 
	# drop indices
	for(i in seq_along(in_process)){
		
		ind <- year$ind[i]
		ind <- ind[ind > 0]	
		if(length(ind) > 0) in_process[[i]] <- in_process[[i]][-ind]
	}
	
	# E) Lists of authors
	pattern <- '^Authors:? |^By[:]? [A-Z]'
	content_chunks(in_process, pattern)
	auth <- extract_and_index(in_process, pattern=pattern)
	
	# extract the whole of those paragraphs
	output_table$auth_para <- mapply(function(i,j) {xx <- in_process[[i]][j]
		  											if(length(xx) > 0) xx else NA},
		  							 seq_along(auth$ind), auth$ind)
		  							 
	# drop indices
	for(i in seq_along(in_process)){
		
		ind <- auth$ind[i]
		ind <- ind[ind > 0]	
		if(length(ind) > 0) in_process[[i]] <- in_process[[i]][-ind]
	}
	
	# what is left is _mostly_ 'abstract' but some trimming and tidying.
	
	for(i in c(18,20,21)){
		output_table$year_para[i] <- in_process[[i]][1]
		in_process[[i]][1] <- ""
	}
	
	output_table$year_para[26] <- in_process[[26]][11]
	in_process[[26]][11] <- ""
	
	output_table$year_para[27] <- in_process[[27]][11]
	in_process[[27]][11] <- ""
	
	for(i in c(29:34,44,45)){
		output_table$auth_para[i] <- in_process[[i]][1]
		in_process[[i]][1] <- ""
	}
	
	in_process[[43]][c(3,7)] <- ''
	
	# Now handle the remains as abstract
	# - strip internal new lines - they're a mess
	in_process <- lapply(in_process, gsub, pattern='\n', replacement=' ')
	# - join multiple paragraphs together
	output_table$description <- sapply(in_process, paste, collapse='\n\n')
	
	# Clean up columns
	
	# - description: remove any abstract tag
	output_table$description <- gsub('^Abstract[:. \n]*|^ABSTRACT[:. \n]*|^Highlights[:. \n]*|^Summary[:. \n]*','', scrubCrap(output_table$description))
	
	# - merge authors and 'year' info
	output_table$auth_para <- scrubCrap(gsub('^Authors:? |^By[:]? ','', output_table$auth_para))
	output_table$auth_para <- scrubCrap(gsub(' ?• ?| ?· ?',', ', scrubCrap(output_table$auth_para)))
	output_table$auth_para <- ifelse(is.na(output_table$auth_para), '', output_table$auth_para)
	output_table$year_para <- ifelse(is.na(output_table$year_para), '', output_table$year_para)
	
	output_table$citation <- scrubCrap(with(output_table, paste(auth_para, year_para)))

################################################
## NOW CHECK OUTPUTS AGAINST LINKS FROM PROJECTS 
################################################
	
	# fixes
	# - duplicated titles?
	output_table$title[39] <- 'The Direct and Indirect Impacts of Logging on Mammals in Sabah, Borneo [Presentation]'
	any(duplicated(output_table$title))
	
	# do all outputs_from_projects have a match in the outputs titles	
	any(is.na(match(outputs_from_projects$title, output_table$title)))

################################################
## Last components and checking on projects and output pairings
################################################
	
	# assemble image and file folders	
	out_image_proj <- file.path(output_folder, 'images/projects')
	out_image_outputs <- file.path(output_folder, 'images/outputs')
	out_files_outputs <- file.path(output_folder, 'files/outputs')
	
	dir.create(out_image_proj, recursive=TRUE)
	dir.create(out_image_outputs, recursive=TRUE)
	dir.create(out_files_outputs, recursive=TRUE)
	
	# copy the project images into a folder
	for(i in seq_along(projects$img_file)){
		
		f <- gsub('\\.\\./','', projects$img_file[i])
		if(!is.na(f)){
			if(file.exists(f)){
				projects$img_file[i] <- basename(f)
				file.copy(f, file.path(out_image_proj, basename(f)))					
			} else {
				stop('Missing image')
			}
		}	
	}
	
	# copy the output images into a folder
	for(i in seq_along(output_table$picture)){
		
		f <- gsub('\\.\\./','', output_table$picture[i])
		if(!is.na(f)){
			if(file.exists(f)){
				file.copy(f, file.path(out_image_outputs, basename(f)))					
			} else {
				stop('Missing image')
			}
		}	
	}
		
	# copy the output files into a folder
	for(i in seq_along(output_table $file)){
		
		f <- gsub('\\.\\./','', output_table$file[i])
		if(!is.na(f)){
			if(file.exists(f)){
				file.copy(f, file.path(out_files_outputs, basename(f)))					
			} else {
				stop('Missing file')
			}
		}	
	}
	
	# final table structure tweaks
	projects$requires_ra <- grepl("Research Assistant", projects$resources)
	projects$requires_vehicle <- grepl("Vehicle", projects$resources)
	projects$resource_notes <- scrubCrap(gsub("Research Assistant\\(s\\),? ?|Vehicle,? ?|Other :|None Required",'', scrubCrap(projects$resources)))
	projects$resources <- NULL
	
	# turn dates into iso format strings
	projects$start_date <- format(projects$start_date)
	projects$end_date <- format(projects$end_date)
	
	# rename the id field. Web2py wants its own id field to be 
	# a serial unique and preloading values on that is a mistake.
	# So, load as legacy id field, match up on the DB load in the 
	# fixtures and never use again
	projects$legacy_project_id <- projects$id
	projects$id <- NULL
	
	# get rid of the image paths, because the new location is hardcoded
	# into the loading script in the web2py fixtures files
	projects$img_file <- basename(projects$img_file)
	
	write.csv(projects, file=file.path(output_folder, 'project_inputs.csv'))
	
	# and outputs
	todrop <- c("n_paras", "year_para", "auth_para")
	output_table <- output_table[, - which(names(output_table) %in% todrop)]
	
	output_table$format[output_table$format=='Thesis'] <- 'Masters Thesis'
	output_table[46,]$format <- 'PhD Thesis'
	
	# get rid of the image paths, because the new location is hardcoded
	# into the loading script in the web2py fixtures files
	output_table$picture <- basename(output_table$picture)
	output_table$file <- basename(output_table$file)
	
	# now need to add in a legacy output id to provide linking within
	# the new database structure which has its own ids
	output_table$legacy_output_id <- output_table$id
	output_table$id <- NULL
	
	write.csv(output_table,file=file.path(output_folder,  "output_inputs.csv"))
	
	# put together entries for the project_outputs mapping table
	outputs_from_projects$legacy_output_id <- output_table$legacy_output_id[match(outputs_from_projects$title, output_table$title)]
	outputs_from_projects$legacy_project_id <- outputs_from_projects$project_id
	outputs_from_projects$project_id <- NULL
	
	outputs_from_projects$added_by <- 1
	outputs_from_projects$date_added <- Sys.Date()
	
	write.csv(outputs_from_projects[, -1:-3],file=file.path(output_folder,  "project_outputs_inputs.csv"))
	
################################################
## User tables and project members
################################################

# correct single idiosyncracies

complex <- projects$researchers[projects$id == 45]
complex <- gsub('[;,]', ':', complex)
complex <- gsub('):', '),', complex)
projects$researchers[projects$id == 45] <- complex


projects$researchers[projects$id == 51] <- "Mohd Nurazmeel Bin Mokhtar, Dr. Arman Hadi Fikri"


project_members <-  gsub(', Jr.',' Jr.', projects$researchers)
project_members <-  gsub('; ?| ?& ?| and ', ',', project_members)

project_members <- strsplit(project_members, ',')
n <- sapply(project_members, length)

project_members <- data.frame(project_id = rep(projects$legacy_project_id, times=n),
							   contact_email = rep(projects$contact_email, times=n),
                              text = unlist(project_members))

# separate out stuff in parentheses (roles, locations)
project_members$paren_data <- extract_re('\\([^\\)]+\\)', project_members$text)
project_members$project_member <- scrubCrap(extract_re('^[^\\()]+\\(?', project_members$text))
project_members$project_member <- gsub(' +\\($', "", project_members$project_member)

# scrub off titles
pattern <- '^Drs?\\.? +|^Profs?\\.? +|Ass\\. Prof\\. |Miss |Mr |PD Dr. '
project_members$title <- extract_re(pattern, project_members$project_member)
project_members$project_member <- gsub(pattern, '', project_members$project_member)

## Now try and recognise individuals with multiple entries

# split last names
project_members$last_name <- extract_re('[A-Za-z]+$', project_members$project_member)
project_members$first_name <- gsub('[A-Za-z]+$', '', project_members$project_member)

# sort into individual blocks
project_members <- project_members[order(project_members$last_name, project_members$first_name),]

# this is now easier to edit by hand than by code, so output and tweak
# and then reload to split into project members and users tables

write.csv(project_members, file.path(output_folder, 'project_and_users_to_be_edited.csv'))

# load cleaned file
projects_users <- read.csv(file.path(output_folder, 'project_and_users_edited.csv'), stringsAsFactors=FALSE, na.string=c('', 'NA'))
projects_users <- as.data.frame(lapply(projects_users, scrubCrap), stringsAsFactors=FALSE)
projects_users$legacy_project_id <- as.numeric(projects_users$legacy_project_id)

unique(projects_users$Project_role)
unique(projects_users$Institution)
unique(projects_users$title)

# now look for unique combinations to be users - excluding project_id and role
projects_users$full <- with(projects_users, paste(last_name, first_name, sep=', '))
users <- split(projects_users[,-c(1,3)], projects_users$full)

# If just one value and NA, then replace, and get unique rows
fillInAndReduce <- function(df){
	
	for(i in 1:ncol(df)){
		
		vals <- unique(na.omit(df[,i]))
		if(length(vals)==1){
			df[is.na(df[,i]), i] <- vals
		}
	}
	return(unique(df))
}

# fill in and check that we only end up with a single row for each, then 
# collapse back into a single data.frame
users <- lapply(users, fillInAndReduce)
users[sapply(users, nrow) != 1]
users <- unsplit(users, 1:length(users))

# check for dupes
users$contact_email[which(duplicated(users$contact_email))]
users$full[which(duplicated(users$full))]

# Great. Now have a list of users, so extract project members
users$legacy_user_id <- seq_along(users$full)

projects_users$legacy_user_id <- users$legacy_user_id[match(projects_users$full, users$full)]
projects_users <- projects_users[,c('legacy_project_id', 'legacy_user_id', 'Project_role')]

# and export everything
# note that the fixtures file again has to handle joining up the projects 
# and members under their new id numbers

names(users) <- c("email", "institution", "title", "last_name", "first_name", "full", "legacy_user_id")
names(users) <- paste('auth_user', names(users), sep='.')
write.csv(users, file.path(output_folder, 'Users_table.csv'))

names(projects_users) <- c("legacy_project_id", "legacy_user_id", "project_role")
write.csv(projects_users, file.path(output_folder, 'project_members_table.csv'))


################################################
## Species Profiles
################################################


## Great now to handle the matching outputs
## - need to check those listed with a project against those
#    in the outputs table

# parse the html of the page to make it easier to extract
pages <- dir('animal-sightings', recursive=TRUE, full=TRUE)
pages <- pages[!grepl('/feed/',pages)]


# db table 
species_table <- data.frame(id = integer(),
							 binomial=character(),
							 common_name=character(),
						     iucn_status=character(),
						     global_population=character(),
						     local_abundance=character(),
						     in_primary = logical(),
						     in_logged =  logical(),
						     in_plantation =  logical(),
						     animal_facts=character(),
						     where_do_they_live=character(),
						     habitat=character(),
						     what_do_they_eat=character(),
						     who_eats_them=character(),
						     threatened_by=character(),
						     image_link=character(),
						     image_href=character(),
						     image_title=character(),
						     google_scholar_link=character(),
						     wikipedia_link=character(),
						     eol_link=character(),
						     iucn_link=character(),
						     arkive_link=character(),
						     gbif_link=character(),
						     stringsAsFactors=FALSE)

for(i in seq_along(pages)){
	
	# hmtl 
	html <- htmlTreeParse(file=pages[i], useInternalNodes=TRUE)
	
	# species name (not consistently in page content)
	# species_name <- xpathSApply(html, '//*[contains(concat( " ", @class, " " ), concat( " ", "h1title", " " ))]', 'xmlValue')
	species_name <- xpathSApply(html, '//title', 'xmlValue')
		
	re <- regexpr('\\([A-Za-z ]+\\)',species_name)
	binomial <- regmatches(species_name, re)
	binomial <- substr(binomial, 2, nchar(binomial)-1)
	re <- regexpr('^[A-Za-z ]+',species_name)
	common_name <- gsub(' $', '', regmatches(species_name, re))
	
	# subset to content
	content <- xpathSApply(html, '//*[(@id = "entry-content")]')[[1]]
	# images
	images <- xpathSApply(content, './/img')
	# paragraphs
	paras <- xpathSApply(content, './/p', 'xmlValue')
	#links 
	links <- xpathSApply(content, './/a')
	
	# parse text
	global_pop <- gsub('Global population trend: ', '', paras[1])
	local_abundance <- gsub('At SAFE Project: ', '', paras[2])

	# get the other content (from para 7 onwards)
	paras <- paras[7:length(paras)]
	paras <- paras[paras != ""]
	
	where <- which(paras == "Where do they live?")
	facts <- 1:(where - 1)
	habitat <- which(paras =="Habitat:")                                                                                                                                                                                                                                                                                                                                                                                                                     
	food <- which(paras =="What do they eat?")                                                                                                                                                                                                                                                                                                                                                                                                                  
	predators <- which(paras =="Who eats them?")                                                                                                                                                                                                                                                                                                                                                                                                                  
	threat <- which(paras =="Threatened by..")                                                                                                                                                                                                                                                                                                                                                                                                                     

	where <- if(length(where) > 0) paras[where + 1] else ''
	habitat <- if(length(habitat) > 0) paras[habitat + 1] else ''
	food <- if(length(food) > 0) paras[food + 1] else ''
	predators <- if(length(predators) > 0) paras[predators + 1] else ''
	threat <- if(length(threat) > 0) paras[threat + 1] else ''
	
	facts <- paste(paras[facts], collapse='\n')

	# other content is in image formatting
	img <- xpathSApply(images[[1]], '.', xmlGetAttr, 'src')
	iucn <- basename(xpathSApply(images[[2]], '.', xmlGetAttr, 'src'))
	
	local_habitats <- sapply(images[3:5], xpathSApply , path='.', fun=xmlGetAttr, 'src') 
	local_habitats <- grepl('Colour', local_habitats)
	
	# get the links out
	link_urls <- sapply(links, xpathSApply, path='.', xmlGetAttr, 'href')


	link_set <- character(6)
	link_pattern <- c('scholar.google', 'noeasymatchhere', 'eol.org','iucnredlist.org','arkive.org','gbif.org')
	for(j in seq_along(link_set)){
		ind <- 	which(grepl(link_pattern[j], link_urls))
		link_set[j]	<- if(length(ind) > 0) unique(link_urls[ind]) else ''
	}
	# no unique pattern for the wiki entry so assume it is the next link after google
	ind <- 	which(grepl(link_pattern[1], link_urls))
	link_set[2]	<- if(length(ind) > 0)  link_urls[ind+1]	
	
	species_table[i, ] <- list(i, binomial, common_name, iucn, global_pop, local_abundance,
								in_primary=local_habitats[1], in_logged=local_habitats[2],
								in_plantation=local_habitats[1], animal_facts=facts,
								where_do_they_live=where, habitat=habitat, what_do_they_eat=food,
								who_eats_them=predators, threatened_by=threat, image_link=img,
								image_href=link_urls[1], image_title=xpathSApply(links[[1]], '.', xmlGetAttr, 'title'),
							    google_scholar_link=link_set[1], wikipedia_link=link_set[2],
							    eol_link=link_set[3], iucn_link=link_set[4],
							    arkive_link=link_set[5], gbif_link=link_set[6])

}

# tidy up the IUCN link
iucn_status <- species_table$iucn_status
iucn_status <- gsub('IUCN-|-600x12[34].png', '', iucn_status)
species_table$iucn_status <- iucn_status <- gsub('-', ' ', iucn_status)

# get the names ready for import into web2py
names(species_table) <- paste('species_profile', names(species_table), sep='.')
write.csv(species_table, file.path(output_folder, 'species_inputs.csv'), row.names=FALSE)

##----------------------------------------------
##  field contacts
##----------------------------------------------

url <- "file:///Users/dorme/Research/SAFE/SAFE_website_plan/wget_existing_website/www.safeproject.net/index.html%3Fp=288.html"

contents <- htmlTreeParse(url, useInternal=TRUE)

rows <- xpathApply(contents, '//tr')

pic <- unlist(sapply(rows, xpathApply, path='.//img', 'xmlGetAttr', 'src'))


for(p in pic){
	
	file.copy(p, file.path(output_folder, 'images','contacts', basename(p)))
	
}

col2 <- xpathSApply(contents, '//*[contains(concat( " ", @class, " " ), concat( " ", "column-2", " " ))]', xmlValue)
col2 <- strsplit(col2, '\r\n')
name <- sapply(col2, '[', 1)
name <- gsub('“|”', '"', name)
role  <- sapply(col2, '[', 2)

cbind(name, role, basename(pic))


##----------------------------------------------
##  Scraping the blog posts
##----------------------------------------------

pages <- c('http://www.safeproject.net/category/blog/page/1/', 'http://www.safeproject.net/category/blog/page/2/')
posts <- list()

# get index pages - blocks of content consisting of anchors each containing a list item
for(p in pages){
	contents <- htmlTreeParse(p, useInternal=TRUE)
	content_block <- xpathApply(contents, '//*[(@id = "cont-content")]')
	posts <- c(posts, xpathApply(content_block[[1]], './/a'))
}

# from the list of nodes, get the titles, thumbnail image, date and content URL
titles <- unlist(lapply(posts, xpathSApply, path='.//h2', xmlValue))
thumb <- unlist(lapply(posts, xpathSApply, path='.//img', 'xmlGetAttr','src'))
date <- unlist(lapply(posts, xpathSApply, path='.//*[contains(concat( " ", @class, " " ), concat( " ", "postmeta", " " ))]', xmlValue)) 
url <- unlist(lapply(posts, xpathSApply, path='.', 'xmlGetAttr','href'))[-c(13,22)]

authors <- html_out <- character(length=length(url))


# ordinarily the images would be linked in through the download/upload mech
# but that would be a faff here, so hard code them in
blog_image_dir <- '~/Research/SAFE/Web2Py/web2py/applications/SAFE_web/static/images/blog_legacy'
dir.create(blog_image_dir, recursive=TRUE)

for( i in seq_along(url)){
	
	contents <- htmlTreeParse(url[i], useInternal=TRUE)
	# get content - scrape the entry content, which annoyingly includes the footer carousel.
	contents <- xpathApply(contents, '//*[(@id = "entry-content")]')[[1]]
	auth <- xpathSApply(contents, './/strong', xmlValue)
	authors[i] <- if(length(auth) > 0) auth else ''
	
	# grab a list of nodes containing paragraphs and images,
	# sometimes images are embedded in paragraphs, but since
	# we only grab text from 'p' nodes, they get elided
	contents <- xpathApply(contents, './/p | .//img')

	# dispose of carousel image links
	element_class <- lapply(contents, xpathSApply, '.', 'xmlGetAttr', 'class')	
	element_class <- sapply(element_class, function(x) if(length(x) == 0) '' else x)
	carousel <- which(element_class == "attachment-thumbnail wp-post-image")
	contents <- contents[-carousel]
	
	# get the type of what is left
	element_type <- sapply(contents, xpathSApply, '.', 'xmlName')

	# recreate an html string
	html <- ""

	for(ind in seq_along(contents)){
		
		switch(element_type[ind],
			'p' = {
				txt <- scrubCrap(xmlValue(contents[[ind]]))
				if(! txt %in% c('', 'Back To Previous Page')){
					html <- c(html, paste('<p>', xmlValue(contents[[ind]]), '</p>', sep=''))}
			},
			'img' ={
				
				# get the attributes
				attrs <- xpathSApply(contents[[ind]], '.', 'xmlAttrs')
				at <-as.list(attrs)
				names(at) <- rownames(attrs)
				
				# download image, but for some reason, some of the images are embedded as base64 data streams.
				if( substr(at$src,1,4) == 'data'){
					# character mode base64
					data <- substr(at$src,24, nchar(at$src))
					data <- base64Decode(data, mode='raw')
					at$src <- paste(gsub(' ','_', titles[i]), '_', ind, '.jpeg', sep='')
					outfile <- file.path(blog_image_dir, at$src)
					writeBin(data, outfile)
					j <- readJPEG(outfile)
					size <- dim(j)
					at$height = size[1]
					at$width = size[2]
				} else {
					# use libcurl download to follow http > https and apply any sizing args
					base <- gsub('\\?.+$', '', basename(at$src)) # clean basename with no args
					download.file(at$src, file.path(blog_image_dir, base), method='libcurl')
					# hard code the paths to the images, this is brittle
					at$src<- base
				}
				
				at$src <- file.path('/safe_web/static/images/blog_legacy', at$src)
				html <- c(html, 	paste("<img src='", at$src, "' width='", at$width, "' height='", at$height, "'>", sep=''))
				
			})
		html_out[i] <- paste(html, collapse='')
	}
}
# format date posted
date <- gsub('Posted ', '',date)
date <- gsub('(th|rd|st|nd),', '', date)
date <- as.character(strptime(date, '%B %e %Y.'))

# copy the blog thumbnail images into a folder
thumb_dir <- file.path(output_folder, 'images/blog_thumbnails')
dir.create(thumb_dir, recursive=TRUE)
for(f in thumb){
	download.file(f, file.path(thumb_dir, basename(f)))	
}
thumb <- basename(thumb)

# authors
authors <- gsub('^By ', '', authors)

# titles
titles <- scrubCrap(titles)
re <- ' ?[-,] [Bb]y'
re <- regexpr(re, titles)
authors2 <- ifelse(re > 0, substr(titles, re+attr(re, 'match.length') +1, stop=nchar(titles)), '')
titles <- ifelse(re > 0, substr(titles, 1, re-1), titles)
authors <- paste(authors, authors2, sep='')

# output
blogdata <- data.frame(date_posted = date,
					thumb=thumb,
				   title = titles,
				   authors = authors,
				   content = html_out,
				   stringsAsFactors=FALSE)


write.csv(blogdata, file.path(output_folder, 'blog_inputs.csv'), row.names=FALSE)




##----------------------------------------------
##  Scraping the news posts
##----------------------------------------------

page <- 'http://www.safeproject.net/category/news/page/XXX/'
posts <- list()

# get index pages - blocks of content consisting of anchors each containing a list item
for(p in 1:4){
	contents <- htmlTreeParse(sub('XXX',p, page), useInternal=TRUE)
	content_block <- xpathApply(contents, '//*[(@id = "cont-content")]')
	posts <- c(posts, xpathApply(content_block[[1]], './/a'))
}


# from the list of nodes, get the titles, thumbnail image, date and content URL
# - after removing some inactive nodes
containstitle <- lapply(posts, xpathSApply, path='.//h2', xmlValue)
posts <- posts[as.logical(sapply(containstitle, length))]

title <- unlist(lapply(posts, xpathSApply, path='.//h2', xmlValue))
thumb <- unlist(lapply(posts, xpathSApply, path='.//img', 'xmlGetAttr','src'))
date <- unlist(lapply(posts, xpathSApply, path='.//*[contains(concat( " ", @class, " " ), concat( " ", "postmeta", " " ))]', xmlValue)) 
url <- unlist(lapply(posts, xpathSApply, path='.', 'xmlGetAttr','href'))

html_out <- character(length=length(url))

# ordinarily the images would be linked in through the download/upload mech
# but that would be a faff here, so hard code them in
news_image_dir <- '~/Research/SAFE/Web2Py/web2py/applications/SAFE_web/static/images/news_legacy'
dir.create(news_image_dir, recursive=TRUE)

for( i in seq_along(url)){
	
	contents <- htmlTreeParse(url[i], useInternal=TRUE)
	# get content - scrape the entry content, which annoyingly includes the footer carousel.
	contents <- xpathApply(contents, '//*[(@id = "entry-content")]')[[1]]

	# get the children nodes
	contents_child <- xmlChildren(contents)
	
	# find the comment showing the carousel start
	carousel <- which(names(contents_child) == 'comment')
	contents_child <- contents_child[1:(carousel-1)]
	content_type <- names(contents_child)
	
	# what's left is a mix of text and paragraphs, but a lot of the text is just tabs and newlines
	just_space <- logical(length=length(contents_child))
	for(j in seq_along(just_space)){
		if(content_type[j] == 'text'){
				just_space[j] <- grepl('^[\t\n]+$', xmlValue(contents_child[[1]]))
		}
	}	
	
	contents_child <- contents_child[! just_space]

	# are there any embedded images in those remaining nodes
	img <- lapply(contents_child, xpathApply, './/img')
	n_img <- sapply(img, length)
	if(any(n_img > 0)){
		img <- unlist(img) # drops empty matches
		img_paths <- sapply(img, xpathApply, '.', 'xmlGetAttr', 'src')
		for(p in img_paths)	download.file(p, file.path(news_image_dir, basename(p)), method='libcurl')
	}
	
	# paste all the nodes together as text
	html <- paste(sapply(contents_child, saveXML), collapse='')
	
	# sub in new image links - doesn't handle other links, which aren't as easy to fix
	pattern <- 'http://www.safeproject.net/wp-content/uploads/[0-9]+/[0-9]+/'
	html_out[i] <- gsub(pattern, '/safe_web/static/images/news_legacy/', html)
	
}

# format date posted
date <- gsub('Posted ', '',date)
date <- gsub('(th|rd|st|nd),', '', date)
date <- as.character(strptime(date, '%B %e %Y.'))

# copy the blog thumbnail images into a folder
thumb_dir <- file.path(output_folder, 'images/news_thumbnails')
dir.create(thumb_dir, recursive=TRUE)
for(f in thumb){
	try(download.file(f, file.path(thumb_dir, basename(f)))	)
}
thumb <- basename(thumb)

# titles
titles <- scrubCrap(titles)

# output
news_data <- data.frame(date_posted = date,
						thumb=thumb,
				   		title = titles,
					   content = html_out,
					   stringsAsFactors=FALSE)

write.csv(news_data, file.path(output_folder, 'news_inputs.csv'), row.names=FALSE)

