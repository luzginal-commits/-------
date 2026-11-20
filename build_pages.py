"""Собрать автономную версию для GitHub Pages: python build_pages.py."""

from pathlib import Path
import base64
import re

ROOT = Path(__file__).resolve().parent

BROWSER_RULES = """
// Автономная игровая логика: Python-сервер для этой версии не нужен.
function browserShot(role,direction,power,history){
 if(role==='keeper'){
  const corner=Math.random()<.75;
  const shotX=corner?(Math.random()<.5?.12:.72)+Math.random()*.16:.12+Math.random()*.76;
  const shotY=corner?(Math.random()<.5?.24:.64)+Math.random()*.12:.24+Math.random()*.52;
  return {keeper:direction,shotX,shotY,outcome:'goal'};
 }
 const weights=[1,1,1];
 [...history].reverse().forEach((previous,age)=>weights[previous]+=2.4/(age+1));
 const n=history.length;
 if(n>=2&&history[n-1]===history[n-2])weights[history[n-1]]+=4;
 else if(n>=3&&history[n-1]===history[n-3])weights[history[n-2]]+=5;
 let draw=Math.random()*weights.reduce((sum,w)=>sum+w,0),keeper=2;
 for(let i=0;i<3;i++){draw-=weights[i];if(draw<0){keeper=i;break;}}
 if(power<=45)return {keeper:direction,outcome:'save'};
 if(power>92)return {keeper,outcome:'miss'};
 const reaction=Math.max(.08,.6-(power-46)*.011);
 if(keeper!==direction&&Math.random()<reaction)keeper=direction;
 const chance=power<72?1:Math.max(.58,.86-(power-72)*.012);
 return {keeper,outcome:keeper===direction&&Math.random()<chance?'save':'goal'};
}
"""


def build():
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    if "  const response=await fetch('/shot'" in source:
        start = source.index("  const response=await fetch('/shot'")
        end = source.index("  const weakCatch=", start)
        source = source[:start] + "  const result=browserShot(role,direction,power,history);\n" + source[end:]
        source = source.replace("<script>\n", "<script>\n" + BROWSER_RULES, 1)
    elif "function browserShot(" not in source:
        raise ValueError("Не найдена игровая логика для автономной версии")
    source = source.replace(
        "Проверь, что python app.py запущен, и попробуй снова.",
        "Обнови страницу и попробуй снова.",
    )
    if "fetch(" in source:
        raise ValueError("В автономной версии остался запрос к серверу")
    for name in ("aim-map.png", "aim-head.png", "aim-reward-photo.png"):
        asset = ROOT / "assets" / name
        image_id = name.removesuffix(".png")
        image_data = "data:image/png;base64," + base64.b64encode(asset.read_bytes()).decode("ascii")
        pattern = rf'(<img id="{image_id}"[^>]*\bsrc=")[^"]*(")'
        source, count = re.subn(pattern, lambda match: match[1] + image_data + match[2], source)
        if count != 1:
            raise ValueError(f"Не найдено изображение {image_id}")
    # Один автономный файл для локальной игры и публикации.
    (ROOT / "index.html").write_text(source, encoding="utf-8")
    print(f"Ready: {ROOT / 'index.html'}")


if __name__ == "__main__":
    build()
