library('XLConnect')

# code to cross check what was extracted from the old website against Liv's records
setwd('/users/dorme/Research/SAFE/Web2Py/web2py/applications/SAFE_web/private/db_preload_data')


## PROJECTS according to Liv and Earthcape

liv_project_wb <- loadWorkbook('liv_data_files/Approved projects.xlsx')
liv_project_data <- readWorksheet(liv_project_wb, 1)

liv_earthcape_wb <- loadWorkbook('liv_data_files/01 Project.xlsx')
liv_earthcape_data <- readWorksheet(liv_earthcape_wb, 1)

web_project_data <- read.csv('project_inputs.csv', stringsAsFactors=FALSE)

str(liv_project_data)
str(liv_earthcape_data)
str(web_project_data)

# CURE SOME TYPOS/VARIANTS

web_project_data$title[web_project_data$title == 'Effects of fragmentation on seedling recruitment, litter fall and decomposition ratesSeedling recruitment, litter fall and decomposition rates'] <-  "Effects of fragmentation on seedling recruitment, litter fall and decomposition rates"

web_project_data$title[web_project_data$title  == "Woody debris as habitat for saproxylic arthropods"] <- "The role of woody debris as habitats for saproxylic arthropods"

web_project_data$title[web_project_data$title  == "Ecology of a large squamate (Varanus salvator macromaculatus)"] <- "Investigating the ecology of a large squamate (Varanus salvator macromaculatus) in altered forest ecosystems, Sabah, Borneo, Malaysia."

liv_project_data$Project[liv_project_data$Project == "Retaining Riparian Reserves in Oil Palm Plantations and in a Highly Degraded Forest Area for Mammals Conservation"] <- "Retaining Riparian Reserves in Oil Palm Plantations and in a Highly Degraded Forest Area for Mammal Conservation"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Covariation between biodiversity and ecosystem functions across a modified tropical landscape: influences of environmental policies."] <- "Covariation between biodiversity and ecosystem functions"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Different land use effect on earthworms at SAFE Project site in Sabah, Borneo"] <- "Land use effect on earthworms"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Quantifying Predation Pressure Along a Gradient of Land Use Intensity in Sabah, Borneo"] <- "Quantifying Predation Pressure Along a Gradient of Land Use Intensity"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Functional diversity and community assembly patterns in ant (Hymenoptera: Formicidae) communities across a forest disturbance gradient in Sabah, Malaysia"] <- "Functional diversity and community assembly patterns in ant (Hymenoptera: Formicidae) communities across a forest disturbance gradient in Sabah"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Impacts of habitat sizes on butterfly communities at SAFE Project, Sabah"] <- "Impacts of habitat size on butterfly communities"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Parasite Biodiversity of Sabah Province, Borneo, Malaysia"] <- "Aquatic parasite biodiversity"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Quantifying Seed Dispersal Rate Amongst Vertebrates Vs Invertebrates Along a Land-Use Gradient"] <- "Partitioning Seed Dispersal Rate Amongst Vertebrates Vs Invertebrates Along a Land-Use Gradient"

liv_earthcape_data$Name[liv_earthcape_data$Name == "Termite Fauna (Isoptera) at SAFE (Stability of Altered Forest Ecosystems) Experimental Plots, Tawau, Sabah, Malaysia"] <- "Variations in termite fauna (Isoptera) in altered forest habitats"


# make copies to clean and match

liv_titles <- liv_project_data$Project
web_titles <- web_project_data$title
earthcape_titles <- liv_earthcape_data$Name

# some simple sanitising
liv_titles <- tolower(liv_titles)
liv_titles <- gsub("’","'", liv_titles)
liv_titles <- gsub("[ .]+$","", liv_titles)
liv_titles <- gsub("  +"," ", liv_titles)

web_titles <- tolower(web_titles)
web_titles <- gsub("’","'", web_titles)
web_titles <- gsub("[ .]+$","", web_titles)
web_titles <- gsub("  +"," ", web_titles)

earthcape_titles <- tolower(earthcape_titles)
earthcape_titles <- gsub("’","'", earthcape_titles)
earthcape_titles <- gsub("[ .]+$","", earthcape_titles)
earthcape_titles <- gsub("  +"," ", earthcape_titles)

# Look for overlap on project titles
# Web titles have all but the most recent, which are now up on web, so just rescan.
intersect(web_titles, liv_titles)
setdiff(web_titles, liv_titles)
setdiff(liv_titles, web_titles)

# Look for overlap on earthcape project titles, 
# more problematic - 10, of which 7 are "core" and 3 look like standard projects
intersect(web_titles, earthcape_titles)
setdiff(web_titles, earthcape_titles)
setdiff(earthcape_titles, web_titles)

## PEOPLE

liv_user_wb <- loadWorkbook('liv_data_files/MasterList.xlsx')
liv_user_data <- readWorksheet(liv_user_wb, 1)

web_user_data <- read.csv('Users_table.csv', stringsAsFactors=FALSE)

str(web_user_data)
str(liv_user_data)

match(web_user_data$last_name,liv_user_data$Surname)

user_merge <- merge(liv_user_data, web_user_data, 
					by.x=c('Surname', 'Given.name'),
                    by.y=c('last_name', 'first_name'),  all=TRUE)

write.csv(user_merge, file='web_liv_user_merge.csv')

