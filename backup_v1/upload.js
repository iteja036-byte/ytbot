require('dotenv').config();
const{google}=require('googleapis');
const{authenticate}=require('./auth');
const fs=require('fs'),path=require('path');
const TITLE=process.argv[2]||'Amazing Facts You Did Not Know';
const TAGS=(process.argv[3]||'india,facts,trending').split(',');
async function upload(){
  const D=path.join(require('os').homedir(),'ytbot');
  process.chdir(D);
  if(!fs.existsSync('video.mp4')){console.log("ERROR: video.mp4 missing");process.exit(1);}
  const mb=(fs.statSync('video.mp4').size/(1024*1024)).toFixed(1);
  console.log(`Uploading ${mb}MB: ${TITLE}`);
  const auth=await authenticate();
  const yt=google.youtube({version:'v3',auth});
  const script=fs.existsSync('script.txt')?fs.readFileSync('script.txt','utf8').replace(/HOOK:|FACT:|EXPLANATION:|INSIGHT:|CTA:/g,'').substring(0,400).trim():'';
  const desc=`${script}\n\n━━━━━━━━━━━━━━━━━\n🔔 Subscribe for daily videos!\n👍 Like this video\n💬 Comment below\n━━━━━━━━━━━━━━━━━\n\n#Shorts #India #Facts #Trending`;
  const res=await yt.videos.insert({
    part:['snippet','status'],
    requestBody:{
      snippet:{title:TITLE+' #Shorts',description:desc,tags:[...TAGS,'shorts','india','viral','trending'],categoryId:'22',defaultLanguage:'en'},
      status:{privacyStatus:'public',madeForKids:false}
    },
    media:{mimeType:'video/mp4',body:fs.createReadStream('video.mp4')}
  });
  const id=res.data.id;
  console.log(`\n✅ LIVE: https://youtube.com/shorts/${id}`);
  const h=fs.existsSync('upload-history.json')?JSON.parse(fs.readFileSync('upload-history.json')):[];
  h.push({date:new Date().toISOString(),title:TITLE,url:`https://youtu.be/${id}`});
  fs.writeFileSync('upload-history.json',JSON.stringify(h,null,2));
  console.log(`Total uploaded: ${h.length} videos`);
}
upload().catch(e=>{console.error('Upload error:',e.message);process.exit(1);});
