import datetime

@auth.requires_login()
def discussion_board():
    
    # create bespoke view for topics
    # 1) creates a custom button to pass the row id to a custom view 
    # Commented out code here allows the form to show a pretty icon for status, BUT
    # blocks it from being used in searches. So don't do that.
    
    links = [dict(header = '', body = lambda row: A('View topic',_class='button btn btn-default',
                  _href=URL("discussion","view_topic", args=[row.id]),
                  _style='padding: 3px 10px 3px 10px;'))]
    
    form = SQLFORM.grid(db.discussion_topics,
                        fields = [db.discussion_topics.topic,
                                  db.discussion_topics.topic_date,
                                  db.discussion_topics.n_messages,
                                  db.discussion_topics.n_views],
                        headers = {'discussion_topics.n_messages': 'Messages', 
                                   'discussion_topics.topic_date': 'Date',
                                   'discussion_topics.n_views': 'Views'},
                        orderby = ~ db.discussion_topics.topic_date,
                        maxtextlength = 500,
                        deletable=False,
                        editable=False,
                        details=False,
                        create=False,
                        csv=False,
                        links=links)
    
    # insert a new button into the form, where the create new record button would be
    # that redirects to a create new topic form (which populates topic and first post in the topic)
    new_button = A("New topic", _class='btn btn-default',
                   _href=URL("discussion","new_topic"), 
                   _style='padding: 5px 10px 5px 10px;')
    
    form.element('.web2py_console').insert(1, new_button)
    
    
    return dict(form=form)


@auth.requires_login()
def new_topic():
    
    """
    Both creates a new entry in topic and the first message in that topic
    """
    
    form=SQLFORM.factory(db.discussion_topics, 
                         db.discussion_message,
                         fields = ['topic',
                                   'message'])
    
    if form.process().accepted:
        
        # insert topic
        date = datetime.datetime.utcnow().isoformat(),
        topic = {'topic': form.vars.topic, 'topic_user_id': auth.user.id,
                 'topic_date': date, 'n_views': 0, 'n_messages': 1}
        id = db.discussion_topics.insert(**topic)
        
        # insert first message
        msg =  {'topic_id': id, 'parent_id': None, 'depth': 0,
                'message': form.vars.message, 'message_user_id': auth.user.id,
                'message_date':date}

        db.discussion_message.insert(**msg)
        
        redirect(URL('discussion','view_topic', args=id))
    
    return dict(form=form)



@auth.requires_login()
def view_topic():
    
    """
    Pulls all the messages from a topic and displays them
    """
    
    topic_id = request.args(0)
    messages = db(db.discussion_message.topic_id == topic_id).select()
    
    # update the number of views
    topic_record = db.discussion_topics(topic_id)
    topic_record.update_record(n_views = topic_record.n_views + 1)
    topic = topic_record.topic
    
    # - use depth and message_date to sort to work from the deepest messages 
    #   but in chronological order
    messages = sorted(messages, key=lambda x: (x.depth * -1, x.message_date)) 
    
    # each message becomes a bootstrap media object
    left_image = SPAN(_class="glyphicon glyphicon-envelope", _style="font-size: 2em;")
    reply = SPAN(_class="glyphicon glyphicon-pencil", _style="font-size: 1.4em;color:gray", _title='Reply')
     # SPAN('REPLY', _class="label label-default") 
    
    message_div = []
    
    for m in messages:
        m_div = DIV(DIV(left_image, _class='media-left'),
                    DIV(DIV(B(m.message_user_id.first_name + " " + m.message_user_id.last_name),
                            ' (' + str(m.message_date.strftime('%Y-%m-%d %H:%M')) + ')',
                            A(reply, _href=URL('discussion', 'reply_message', args=m.id), _class='pull-right'),
                            _class='media-heading', _style='background-color:gainsboro; padding: 5px 10px 5px 10px;'),
                        P(m.message),
                        _class='media-body'),
                    _class="media")
        message_div.append(m_div)
    
    # now need to nest those messages by parent id - pop them out of the list of messages
    # from tips down to root and insert them back into their parent as a nested DIV
    msg_id = [m.id for m in messages]
    messages = dict(list(zip(msg_id, messages)))
    message_div = dict(list(zip(msg_id, message_div)))
    
    for m in msg_id:
        # grab the message row for lookup and div to insert
        this_msg = messages.pop(m)
        this_div = message_div.pop(m)
        
        # insert the div into the parent div until we get to
        # the root of the message tree
        if this_msg.parent_id is not None:
            parent_div = message_div[this_msg.parent_id]
            parent_div.components[1].components.append(this_div)
    
    return dict(topic = topic, messages=this_div)


@auth.requires_login()
def reply_message():
    
    """
    posts a reply to a message on a topic
    """
    
    parent_id = request.args(0)
    
    form = SQLFORM(db.discussion_message,
                   fields = ['message'])
    
    if form.process(onvalidation=validate_reply_message).accepted:
        # now that the record is created, we can fill in other stuff
        record = db.discussion_message(form.vars.id)
        parent = db.discussion_message(parent_id)
        record.update_record(parent_id=parent.id, 
                             topic_id=parent.topic_id,
                             depth = parent.depth + 1)
        topic = db.discussion_topics(parent.topic_id)
        topic.update_record(n_messages = topic.n_messages + 1)
        
        redirect(URL('discussion','view_topic', args=topic.id))
    
    return dict(form=form)


def validate_reply_message(form):
    
    # input a bunch of housekeeping information
    form.vars.message_user_id = auth.user.id
    form.vars.message_date = datetime.datetime.utcnow().isoformat()
