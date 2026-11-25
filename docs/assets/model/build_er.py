"""Build the three documentation ER figures; no database or application is executed."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans', 'pdf.fonttype':42, 'svg.fonttype':'none'})

def render(name, title, nodes, edges, notes):
    fig, ax = plt.subplots(figsize=(7.1, 7.7))
    ax.set(xlim=(-0.2, 10.8), ylim=(0.2, 12.5))
    ax.axis('off')
    ax.text(5.3,12.15,title,ha='center',fontsize=12,weight='bold')
    w,h=4.4,1.45
    for key,(x,y,heading,fields) in nodes.items():
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.025',edgecolor='#24394a',facecolor='#f2f5f7',linewidth=1))
        ax.text(x+w/2,y+h-.24,heading,ha='center',va='center',fontsize=8 if len(heading)>27 else 9,weight='bold',family='DejaVu Sans Mono')
        ax.plot([x,x+w],[y+h-.48,y+h-.48],color='#24394a',lw=.7)
        ax.text(x+.16,y+h-.67,fields,ha='left',va='top',fontsize=8.3,family='DejaVu Sans Mono',linespacing=1.4)
    for a,b,ca,cb,side in edges:
        xa,ya,*_=nodes[a]; xb,yb,*_=nodes[b]
        if side=='h':
            p=(xa+w,ya+h/2); q=(xb,yb+h/2)
            tx1,ty1=p[0]+.10,p[1]+.18; tx2,ty2=q[0]-.12,q[1]+.18
            ha1,ha2='left','right'
        else:
            if ya>yb:
                p=(xa+w/2,ya); q=(xb+w/2,yb+h)
                tx1,ty1=p[0]+.12,p[1]-.24; tx2,ty2=q[0]+.12,q[1]+.16
            else:
                p=(xa+w/2,ya+h); q=(xb+w/2,yb)
                tx1,ty1=p[0]+.12,p[1]+.12; tx2,ty2=q[0]+.12,q[1]-.22
            ha1=ha2='left'
        ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-',color='#24394a',lw=1.05))
        for x,y,label,ha in [(tx1,ty1,ca,ha1),(tx2,ty2,cb,ha2)]:
            ax.text(x,y,label,fontsize=8,ha=ha,va='center',bbox={'facecolor':'white','edgecolor':'none','pad':.2})
    ax.text(.15,1.5,notes,fontsize=8,va='top',linespacing=1.4)
    fig.subplots_adjust(left=.01,right=.99,top=.99,bottom=.01)
    for ext in ('png','svg','pdf'):
        fig.savefig(ROOT/(name+'.'+ext),dpi=240,facecolor='white')
    plt.close(fig)

def n(col,row,title,fields):
    return (.15+5.9*col,9.9-2.55*row,title,fields)

if __name__=='__main__':
    core={
        'g':n(0,0,'user_group','PK id\nUQ group_number'),
        'u':n(1,0,'app_user','PK id\nFK group_id (NULL)'),
        'gc':n(0,1,'user_group_problem_configuration','PK id; FK group_id\nFK configuration_id + name'),
        's':n(1,1,'problem_session','PK id; FK user_id\nstate; deadline_at'),
        'c':n(0,2,'problem_configuration','PK id\nname'),
        'p':n(1,2,'problem','PK id; FK session_id\nUQ session_id + position'),
        'ci':n(0,3,'configuration_item','PK configuration_id + position\ntype'),
        'b':n(1,3,'backpack_problem','PK/FK id -> problem.id\nЗакрытый контекст'),
    }
    render('er-core','Учётные записи, шаблоны и задачи',core,
           [('g','u','0..1','0..*','h'),('g','gc','1','0..*','v'),('c','gc','1','0..*','v'),('c','ci','1','0..*','v'),('u','s','1','0..*','v'),('s','p','1','0..*','v'),('p','b','1','0..1','v')],
           'AbstractEntity: общие id и created_at, отдельной таблицы нет.\nСвязи ролей и назначений преподавателю уточнены в спецификации.')
    publication={
        'a':n(0,0,'assessment','PK id; FK author_id\nDRAFT / PUBLISHED'),
        't':n(1,0,'custom_task','PK id; FK author_id\ntitle'),
        'i':n(0,1,'assessment_item','PK id; FK assessment_id\nposition; FK custom_task_id'),
        'v':n(1,1,'custom_task_variant','PK id; FK custom_task_id\nstatement + expected_answer'),
        'sv':n(0,2,'assessment_variant','PK id; FK assessment_item_id\nОпубликованные пары'),
        's':n(1,2,'problem_session','PK id\nFK assessment_id (NULL)'),
        'p':n(0,3,'problem','PK id; FK assessment_variant_id\nВыбранная закрытая пара'),
        'hist':n(1,3,'problem','PK id; FK session_id\nСобственный UUID задачи'),
    }
    render('er-publication','Авторский банк и опубликованные варианты',publication,
           [('a','i','1','0..*','v'),('t','v','1','1..*','v'),('i','sv','1','0..*','v'),('sv','p','0..1','0..*','v'),('s','hist','1','0..*','v')],
           'Для опубликованной текстовой позиции закреплены все пары редакции.\nПравка банка не меняет опубликованные копии. Оба блока problem\nобозначают одну таблицу; её связи показаны раздельно.')
    ops={
        'u':n(0,0,'app_user','PK id\nПодтверждённый владелец'),
        's':n(1,0,'problem_session','PK id; FK user_id\nD = deadline_at'),
        'p':n(1,1,'problem','PK id; FK session_id\nstate; result_json'),
        'o':n(1,2,'answer_operation','PK id; FK problem_id, user_id\nИсходное тело; t_in; L; phase'),
        'roles':n(0,1,'user_role','PK user_id + role\nFK user_id'),
        'tg':n(0,2,'teacher_group','PK teacher_id + group_id\nFK app_user; FK user_group'),
    }
    render('er-operations','Зарегистрированные ответы и доступ',ops,
           [('u','s','1','0..*','h'),('u','roles','1','1..*','v'),('s','p','1','0..*','v'),('p','o','1','0..*','v')],
           'У одной задачи могут быть несколько записей REGISTERED.\nПраво CHECKING единственное. У каждого своевременного запроса свой L.\nНазначения преподавателя отделены от членства студента.')
