library(XML)
library(plyr)


# URL of the contents of the researchers directory
res  <- 'http://www.safeproject.net/wp-content/themes/safebysz2/pdf/researchers/'

# extract links
lnks <- htmlParse(res)
anchors <- xpathSApply(lnks, '//a')
href <- sapply(anchors, xmlGetAttr, name='href')
href <- href[grepl('.html$', href)] # dump pdf views

# extract data
dat <- list()
for( i in href ){
	url <- paste(res, i, sep='')
	dat[[i]] <- readHTMLTable(url, stringsAsFactors=FALSE)$tblcontactus	
}

nrows <- sapply(dat, nrow)
table(nrows)

# function to extract the datestamp from the given row
date_stamp <- function(x, r=31){
	date <- x[r,1]
	date <- gsub('This information was submitted on [A-z]+day ', '', date)
	date <- gsub('(th|st|nd|rd) of ', ' ', date)
	date <- strptime(date, format='%d %B %Y')
    x[r,] <- c('timestamp', as.character(as.Date(date)))
    return(x)
}


## ------------
## 31 row tables
## ------------

dat_31 <- dat[nrows == 31]


dat_31 <- lapply(dat_31, date_stamp)

# put them all together
dat_31_integrated <- data.frame(t(dat_31[[1]][,2,drop=FALSE]), stringsAsFactors=FALSE)
names(dat_31_integrated) <- dat_31[[1]][,1]

for ( i in seq(length(dat_31))){	
	dat_31_integrated[i,] <- dat_31[[i]][,2]
}


## ------------
## 23 row tables
## ------------

dat_23 <- dat[nrows == 23]

dat_23 <- lapply(dat_23, date_stamp, r=23)

# put them all together
dat_23_integrated <- data.frame(t(dat_23[[1]][,2,drop=FALSE]), stringsAsFactors=FALSE)
names(dat_23_integrated) <- dat_23[[1]][,1]

for ( i in seq(length(dat_23))){	
	dat_23_integrated[i,] <- dat_23[[i]][,2]
}

## ------------
## Merge
## ------------

names(dat_23_integrated) %in% names(dat_31_integrated)

dat <- rbind.fill(dat_31_integrated, dat_23_integrated)
dat <- dat[order(dat$Name),]


## ------------
## Reconcile
## ------------

usr <- read.csv('final_users.csv', stringsAsFactor=FALSE)

#ids we already know
dat[,'Name:'] <- sub('^Prof |^Professor |^Dr |^Dr\\. |^Mr |^Miss ', '', dat[,'Name:'])

main_email <- match(dat[,'Email address:'], usr$Email)
alt_email <- match(dat[,'Email address:'], usr$alt_email)
name <- match(tolower(dat[,'Name:']), tolower(with(usr, paste(FirstName, LastName))))

dat_unknown <- dat[is.na(main_email) & is.na(alt_email) & is.na(name),]

# any matches on any name parts to last names?
parts <- strsplit(tolower(dat_unknown$Name), ' ')
part_matchs <-  sapply(parts, match, table=tolower(usr$LastName))
part_match <- sapply(part_matchs, function(x) if(all(is.na(x))) return(NA) else return(na.omit(x)))

# OK - lets just take the solid links we've got
matches <- cbind(main_email, alt_email,name)
matches <- apply(matches,1, function(x) if(all(is.na(x))) return(NA) else return(unique(na.omit(x))))
dat$id <- usr$legacy_user_id[matches]

# reduce to most recent unique records
dat_final <- dat[!is.na(dat$id),]
dat_final$timestamp <- as.Date(dat_final$timestamp)

#sort by id and reverse of date
dat_final <- dat_final[rev(order(dat_final$id, dat_final$timestamp)), ] 
dat_final <- dat_final[!duplicated(dat_final$id),]

dat_final <- dat_final[, c('id', 'Passport number:', 'Address:', 'Telephone number:', 
						   'Email:', 'Company:', 'Contact number:',
						   'Policy number:','Medical conditions', 'timestamp')]

names(dat_final) <- c('legacy_user_id', 'passport_number', 'emergency_contact_address', 'emergency_contact_phone',
			   		  'emergency_contact_email', 'insurance_company', 'insurance_emergency_phone',
				      'insurance_policy_number', 'medical_conditions', 'date_last_edited')

write.csv(dat, file='h_and_s_from_web.csv')
write.csv(dat_final, file='final_h_and_s.csv')

