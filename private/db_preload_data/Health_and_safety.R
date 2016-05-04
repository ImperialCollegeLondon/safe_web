library(XML)
library(plyr)


# URL of the contents of the researchers directory
res  <- 'http://www.safeproject.net/wp-content/themes/safebysz2/pdf/researchers/'

# extract links
lnks <- htmlParse(res)
anchors <- xpathSApply(xxx, '//a')
href <- sapply(xxxx, xmlGetAttr, name='href')
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
## Merge and export
## ------------

names(dat_23_integrated) %in% names(dat_31_integrated)

dat <- rbind.fill(dat_31_integrated, dat_23_integrated)
dat <- dat[order(dat$Name),]

write.table(dat, file='health_and_safety.txt', sep='\t')



