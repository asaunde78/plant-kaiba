/**
 * Copyright 2016-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the license found in the
 * LICENSE file in the root directory of this source tree.
 */

var bodyParser = require('body-parser');
var express = require('express');
var app = express();
var xhub = require('express-x-hub');
require('dotenv').config()

app.set('port', (process.env.PORT || 8888));
app.listen(app.get('port'));
console.log("APP SECRET: ", process.env.APP_SECRET)
app.use(xhub({ algorithm: 'sha1', secret: process.env.APP_SECRET }));
app.use(bodyParser.json());

var token = process.env.TOKEN || 'token';
var received_updates = [];

app.get('/', function(req, res) {
  console.log(req);
  res.send('<pre>' + JSON.stringify(received_updates, null, 2) + '</pre>');
});

app.get(['/facebook', '/instagram', '/threads'], function(req, res) {
  if (
    req.query['hub.mode'] == 'subscribe' &&
    req.query['hub.verify_token'] == token
  ) {
    res.send(req.query['hub.challenge']);
  } else {
    res.sendStatus(400);
  }
});

app.post('/facebook', function(req, res) {
  console.log('Facebook request body:', req.body);

  if (!req.isXHubValid()) {
    console.log('Warning - request header X-Hub-Signature not present or invalid');
    res.sendStatus(401);
    return;
  }

  console.log('request header X-Hub-Signature validated');
  // Process the Facebook updates here
  received_updates.unshift(req.body);
  res.sendStatus(200);
});

app.post('/instagram', async function(req, res) {
  console.log('Instagram request body:');
  console.log(req.body);
  // Process the Instagram updates here
  // console.log(req.body.entry[0].messaging)
  if (req.body.entry[0].messaging) {
    console.log(req.body.entry[0].messaging[0].message.attachments)
    let data = req.body.entry[0].messaging[0].message.attachments[0]
    data.content = data.payload.title
    let embed = {title:"video", description:data.payload.title ?? "no title", type:"video", url:data.payload.url, proxy_url:data.payload.url} 
    
    received_updates.unshift(req.body);
    let body  = {
      "content": `[${data.payload.title ?? "No title.."}](${embed.url})`,
      // "embeds":JSON.stringify([embed])
      // "content":"test"
    }
    console.log(body)
    const res = await fetch(process.env.WEBHOOK, {
      method: "POST",
      headers: {
        'Content-Type': 'application/json', 
      },
      body:JSON.stringify(body)
    })
    console.log(res)
  }
  res.sendStatus(200);
});

app.post('/threads', function(req, res) {
  console.log('Threads request body:');
  console.log(req.body);
  // Process the Threads updates here
  received_updates.unshift(req.body);
  res.sendStatus(200);
});

app.listen();