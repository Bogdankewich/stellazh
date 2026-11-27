import cv2,numpy as np,json,os
B=cv2.imread('base.png');H,W=B.shape[:2]
def lin(x):x=x/255.0;return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
def srgb(x):x=np.clip(x,0,1);return np.where(x<=0.0031308,x*12.92,1.055*x**(1/2.4)-0.055)*255
Bl=lin(B.astype(np.float32));Y=(0.0722*Bl[...,0]+0.7152*Bl[...,1]+0.2126*Bl[...,2])
def hex2lin(h):h=h.lstrip('#');rgb=[int(h[i:i+2],16) for i in (0,2,4)];return lin(np.array(rgb[::-1],np.float32))
def m(n):return cv2.imread(f'm_{n}.png',0).astype(np.float32)/255
def feather(a,r=1.2):return cv2.GaussianBlur(a,(0,0),r)
def shade(mask,blur=0,level=0.92,pct=60):
    y=Y if not blur else cv2.GaussianBlur(Y,(0,0),blur)
    ref=np.percentile(y[mask>0.5],pct);return (y/ref*level)[...,None]
def save(name,col_lin,mask,r=1.2):
    a=feather(mask,r);rgba=np.dstack([srgb(col_lin).astype(np.uint8),(a*255).astype(np.uint8)])
    ys,xs=np.where(a>0.01);y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1
    cv2.imwrite(f'out/{name}.webp',rgba[y0:y1,x0:x1],[cv2.IMWRITE_WEBP_QUALITY,88]);return [int(x0),int(y0)]
def swatch_color(path,pct=None):
    s=lin(cv2.imread(path).astype(np.float32));h,w=s.shape[:2]
    if pct is None: c=s[h//4:-h//4,w//4:-w//4].reshape(-1,3).mean(0)
    else:
        f=s.reshape(-1,3);y=f@np.array([.0722,.7152,.2126]);t=np.percentile(y,pct);c=f[(y>t-0.01)&(y<t+0.01)].mean(0)
    return c
os.makedirs('out',exist_ok=True);meta={}
# wallpapers: tile texture, scale so swatch width ~ 180 px
wall=m('wall');sh=shade(wall,blur=25,level=0.93,pct=50)
for n in ['Lana_Macadamia','Lana_Tan','Montagna_Beige','Montagna_Juniper','Bundi_Walnut']:
    s=cv2.imread(f'sw/BIG_{n}.jpg');s=s[s.shape[0]//6:-s.shape[0]//6,s.shape[1]//6:-s.shape[1]//6]
    tw=110 if 'Bundi' not in n else 150
    s=cv2.resize(s,(tw,int(tw*s.shape[0]/s.shape[1])),interpolation=cv2.INTER_AREA)
    sl=lin(s.astype(np.float32));mean=sl.reshape(-1,3).mean(0)
    # flatten low-frequency lighting of the packshot
    low=cv2.GaussianBlur(sl,(0,0),15);r=sl/np.maximum(low,1e-4);tex=(1+(r-1)*0.6)*mean
    th=int(np.ceil(H/tex.shape[0]))+1;tw2=int(np.ceil(W/tex.shape[1]))+1
    T=np.tile(tex,(th,tw2,1))[:H,:W]
    meta['w_'+n]=save('w_'+n,T*sh,wall)
# curtains: solid colour from swatch lit area * full shading
curt=m('curt');sh=shade(curt,level=1.0,pct=75)
for n in ['creme-08','mastic-09','tourterelle-13','macadamia-12','amande-30']:
    sw=cv2.imread(f'sw/F_{n}.jpg');lab=cv2.cvtColor(sw,cv2.COLOR_BGR2LAB).reshape(-1,3).astype(float)
    Lp=np.percentile(lab[:,0],85);ab=np.median(lab[:,1:],0)
    px=cv2.cvtColor(np.uint8([[[Lp,ab[0],ab[1]]]]),cv2.COLOR_LAB2BGR)[0,0].astype(np.float32);c=lin(px)
    meta['c_'+n]=save('c_'+n,c*sh,curt)
# textiles
pil=m('pil');thr=m('throw')
cx=np.array([380,498,907,1035]);xx=np.tile(np.arange(W),(H,1))
idx=np.argmin(np.abs(xx[...,None]-cx[None,None,:]),axis=2)+1
l=np.where(pil>0.5,idx,0);comps=[1,2,3,4]
print('pillows',len(comps))
shp=np.minimum(shade(pil,level=1.0,pct=70),1.08);sht=np.minimum(shade(thr,level=1.0,pct=70),1.15)
C={'bordo':'#4A1A23','olive':'#5A5F30','hunter':'#233126','sage':'#6A7657','cream':'#D8D0C2'}
sets={'t1':(['olive','olive','olive','olive'],'bordo'),
      't2':(['hunter','olive','olive','hunter'],'bordo'),
      't3':(['bordo','olive','olive','bordo'],'sage'),
      't4':(['hunter','sage','sage','hunter'],'olive')}
for k,(pc,tc) in sets.items():
    col=np.zeros((H,W,3),np.float32);msk=np.zeros((H,W),np.float32)
    for i,ci in enumerate(comps):
        mm=(l==ci).astype(np.float32);col+=mm[...,None]*hex2lin(C[pc[i%len(pc)]])*1.0*shp;msk=np.maximum(msk,mm)
    col=col*(1-thr[...,None])+thr[...,None]*hex2lin(C[tc])*1.0*sht;msk=np.maximum(msk,thr)
    meta[k]=save(k,col,msk,1.6)
cv2.imwrite('out/base.webp',B,[cv2.IMWRITE_WEBP_QUALITY,88])
json.dump(meta,open('out/meta.json','w'))
print(meta)
