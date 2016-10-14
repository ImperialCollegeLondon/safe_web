library(XML)
library(jsonlite)

# This code snippet downloads a table of Sabah holidays from
# the web and creates inserts for the backend db
years <- c(2016, 2017)

calFun <- function(year){
	
	# load the calendar days
	url <- sprintf('http://www.officeholidays.com/countries/malaysia/regional.php?list_year=%i&list_region=sabah', year)
	# extract the first table in the page
	cal <- readHTMLTable(url, stringsAsFactors=FALSE)[[1]]
	# drop unneeded columns
	cal <- cal[,c('Date', 'Holiday')]
	
	# format dates
	cal$Date <- gsub('\n.*', paste('', year), cal$Date)
	cal$Date <- strptime(cal$Date, '%B %d %Y')
	
	return(cal)
}

# get the calendar blocks for each year and combine
calendars <- lapply(years, calFun)
calendars <- do.call('rbind', calendars)

# create SQL inserts for public_holidays table
inserts <- sprintf("insert into public_holidays (date,title) values ('%s','%s');\n", calendars$Date, calendars$Holiday)
# tidy out some non-essential ones
inserts <- inserts[! grepl('Mother', inserts)]

cat(inserts, file='public_holidays.sql')
