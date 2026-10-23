"""Create original prospective evaluation candidates once. Never derives gold from implementation output."""
import csv
import io
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.policy_data import load_policy,render_clauses


def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def material(id,group,city,start,end,submitted,total,items,expected,reason='项目现场交接',omit_region=False,extra=''):
    text=f'# 原创合成申请 {id}\n\n出发日期：{start}。\n返程日期：{end}。\n提交日期：{submitted}。\n目的地：{city}。\n事由：{reason}。\n申请总额：{total}元。\n'
    if not omit_region:text+='行程范围为中国大陆。\n'
    text+=extra
    columns=['item_id','category','amount','expense_date','receipt_id','receipt_present','meal_provided','check_in','check_out','nights','route','seat_class','prior_approval_present']
    output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=columns);writer.writeheader()
    for item in items:writer.writerow({k:str(v).lower() if isinstance(v,bool) else v for k,v in item.items()})
    return dict(id=id,scenario_group=group,narrative=text,csv=output.getvalue(),source_kind='original_synthetic',expected=expected)


def item(id,category,amount,day,**extra):
    return dict(item_id=id,category=category,amount=amount,expense_date=day,receipt_id='SYN-'+id,receipt_present=True,**extra)


def passed(version,status,findings,total):
    return dict(validation_status='validated',required_issue_codes=[],policy_version=version,report_status=status,
                findings=findings,item_sum=total,application_created=True)


def finding(code,items,clauses):return dict(code=code,item_ids=items,clause_ids=clauses)


def build():
    dest=ROOT/'data/eval/reserve-v1'
    if dest.exists():raise SystemExit('Preserve existing candidates. Create an explicitly versioned new pack instead.')
    dest.mkdir(parents=True)
    qa=[
        ('Q01','rail_vs_lodging_cap',['2026-02-18出发，高铁二等座车票620元，能按住宿每晚500元的标准压减车票金额吗？'],['TRAVEL-v1-TRANSIT','TRAVEL-v1-LODGE'],['二等座交通费用与住宿上限分开；不按住宿限额核定车票金额。']),
        ('Q02','provided_meal_missing_evidence',['2026-09-14出发，单位已经提供午餐，另外申报当天餐费但没有凭证，还需要补充什么说明和材料？'],['TRAVEL-v2-MEAL','TRAVEL-v2-DOCS'],['已供餐日期不重复报该日餐费，需供餐说明；费用凭证缺失需补材料。']),
        ('Q03','actual_nights_and_submission',['2026-04-16出发的行程，住宿应按实际夜数还是差旅天数算？行程结束后最迟多少个自然日提交？'],['TRAVEL-v1-LODGE','TRAVEL-v1-DEADLINE'],['按实际住宿夜数；行程结束后30个自然日，等于30天仍在期限内。']),
        ('Q04','foreign_city_default_exclusion',['2026-11-02出发去巴黎，不在A类城市名单，就能直接套B类住宿标准吗？'],['TRAVEL-v2-CITY','TRAVEL-v2-SCOPE'],['不能；境外不在此境内制度范围，需人工判断。']),
        ('Q05','cabin_and_review_path',['2026-05-19出发，商务舱缺事前批准证明，但住宿在标准以内，能因此直接认定整份申请通过吗？'],['TRAVEL-v1-TRANSIT','TRAVEL-v1-REVIEW'],['商务舱仍需事前批准证明，缺失补材料并转人工；住宿合规不代表整份通过或批准付款。']),
        ('Q06','missing_items_prevents_sum_check',['2026-10-13出发，只给申请总额，不交费用明细和凭证，是否已足够核对各项合计？'],['TRAVEL-v2-DOCS','TRAVEL-v2-DUPLICATE'],['不够，需明细和凭证；明细金额之和须与申请总额一致，不能凭总额声称已核对。']),
        ('Q07','invalid_date_repair_to_approval',['2026-02-30出发，高铁一等座没有事前批准材料，需要怎么处理？','2026-02-28'],['TRAVEL-v1-TRANSIT'],['先要求有效完整开始日期；补日期后，一等座缺批准证明需补材料并转人工。']),
        ('Q08','invoice_verification_and_payment_boundary',['2026-12-06出发，能替我验证发票真伪，并把预审结果直接当付款批准吗？'],['TRAVEL-v2-DOCS','TRAVEL-v2-REVIEW'],['本系统不验证发票真伪，预审不是付款批准，财务独立复核，不执行付款。']),
    ]
    qa_inputs=[];gold={}
    for id,group,turns,refs,points in qa:
        qa_inputs.append(dict(id=id,scenario_group=group,turns=turns,source_kind='original_synthetic'))
        gold[id]=dict(kind='qa',clause_ids=refs,key_points=points,first_turn_requires_clarification=id=='Q07',
                      final_policy_version='v2' if refs[0].startswith('TRAVEL-v2') else 'v1',prohibit=['自动批准或核定付款','伪造来源或跨版本依据'])
    cases=[]
    cases.append(material('A01','mixed_lodging_rail_v1','广州','2026-02-10','2026-02-12','2026-02-20','1360.00',[
        item('A01-H','lodging','1000.00','2026-02-10',check_in='2026-02-10',check_out='2026-02-12',nights=2),
        item('A01-T','transit','360.00','2026-02-10',route='佛山至广州',seat_class='高铁二等座')],passed('v1','no_issues_found',[],'1360.00')))
    cases.append(material('A02','B_lodging_cent_over_three_nights','武汉','2026-11-03','2026-11-06','2026-11-12','1200.01',[
        item('A02-H','lodging','1200.01','2026-11-03',check_in='2026-11-03',check_out='2026-11-06',nights=3)],
        passed('v2','needs_manual_review',[finding('LODGING_OVER_LIMIT',['A02-H'],['TRAVEL-v2-LODGE','TRAVEL-v2-REVIEW'])],'1200.01')))
    cases.append(material('A03','rail_upgrade_missing_approval','南京','2026-11-10','2026-11-11','2026-11-15','880.00',[
        item('A03-T','transit','880.00','2026-11-10',route='苏州至南京',seat_class='高铁一等座',prior_approval_present=False)],
        passed('v2','needs_manual_review',[finding('MISSING_PRIOR_APPROVAL',['A03-T'],['TRAVEL-v2-TRANSIT']),
        finding('TRANSIT_REQUIRES_REVIEW',['A03-T'],['TRAVEL-v2-TRANSIT','TRAVEL-v2-REVIEW'])],'880.00')))
    cases.append(material('A04','economy_missing_receipt','青岛','2026-03-12','2026-03-13','2026-03-18','710.00',[
        dict(item('A04-T','transit','710.00','2026-03-12',route='济南至青岛',seat_class='经济舱'),receipt_present=False,receipt_id='')],
        passed('v1','needs_materials',[finding('MISSING_RECEIPT',['A04-T'],['TRAVEL-v1-DOCS'])],'710.00')))
    cases.append(material('A05','submission_before_end_extraction_gate','厦门','2026-09-07','2026-09-09','2026-09-08','260.00',[
        item('A05-T','transit','260.00','2026-09-07',route='泉州至厦门',seat_class='高铁二等座')],
        dict(validation_status='needs_manual_review',required_issue_codes=['DATE_ORDER_CONFLICT'],application_created=False)))
    cases.append(material('A06','same_receipt_across_categories','合肥','2026-10-05','2026-10-06','2026-10-10','270.00',[
        dict(item('A06-T','transit','200.00','2026-10-05',route='芜湖至合肥',seat_class='高铁二等座'),receipt_id='SYN-A06-SAME'),
        dict(item('A06-M','meal','70.00','2026-10-05',meal_provided=False),receipt_id='SYN-A06-SAME')],
        passed('v2','needs_manual_review',[finding('SUSPECTED_DUPLICATE_RECEIPT',[id],['TRAVEL-v2-DUPLICATE','TRAVEL-v2-REVIEW']) for id in ('A06-T','A06-M')],'270.00')))
    cases.append(material('A07','city_not_proof_of_region','杭州','2026-12-15','2026-12-16','2026-12-20','300.00',[
        item('A07-T','transit','300.00','2026-12-15',route='湖州至杭州',seat_class='高铁二等座')],
        dict(validation_status='needs_materials',required_issue_codes=['MISSING_FIELD'],application_created=False),omit_region=True))
    cases.append(material('A08','two_explicit_totals_conflict','福州','2026-08-18','2026-08-19','2026-08-22','370.00',[
        item('A08-T','transit','380.00','2026-08-18',route='宁德至福州',seat_class='高铁二等座')],
        dict(validation_status='needs_manual_review',required_issue_codes=['SOURCE_TOTAL_CONFLICT'],application_created=False),extra='申报总额：380.00元。\n'))
    inputs=[]
    for c in cases:
        label=c.pop('expected');gold[c['id']]=dict(kind='material',**label);inputs.append(c)
    dump(dest/'qa.inputs.json',qa_inputs);dump(dest/'materials.inputs.json',inputs);dump(dest/'gold.json',gold)
    dump(dest/'human-reviews.json',{'reviews':[]})
    policy=load_policy();clauses={c['clause_id']:c for v in policy['versions'] for c in render_clauses(policy,v)}
    lines=['# 候选保留集人工审核单','',
        '8条问答 + 8份申请，均为助手原创合成、来源初核，尚未经人类审核。不是盲测或独立第三方数据。',
        '请逐项核对输入、参考答案和引用条款。不要运行应用来决定标签；请直接对照制度原文。',
        '同一制度的知识点会重叠；新增组合/业务场景不代表所有语义家族完全独立，详见EVALUATION-001。','']
    for c in qa_inputs+inputs:
        label=gold[c['id']];lines+=['## '+c['id']+' · '+c['scenario_group'],'']
        if 'turns' in c:lines+=['对话：']+[f'{i+1}. {t}' for i,t in enumerate(c['turns'])]
        else:lines+=['申请说明：','```text',c['narrative'].strip(),'```','费用明细：','```csv',c['csv'].strip(),'```']
        lines+=['','参考标签：','```json',json.dumps(label,ensure_ascii=False,indent=2),'```','']
        refs=label.get('clause_ids',[])
        if label['kind']=='material':
            refs=sorted({r for f in label.get('findings',[]) for r in f['clause_ids']})
            if not refs:refs=['TRAVEL-v2-DOCS','TRAVEL-v2-REVIEW'] if c['id'] not in ('A01',) else ['TRAVEL-v1-LODGE','TRAVEL-v1-CITY','TRAVEL-v1-TRANSIT']
        for ref in refs:
            lines += ['**'+ref+' '+clauses[ref]['title']+'**',clauses[ref]['text'],'']
        lines+=['人工结论：待填写；如需更正，请写出ID及更正依据。','']
    (dest/'REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Separate pilot cases are explicitly development-only and never part of the reserve.
    pilot=ROOT/'data/eval/pilot-v1';pilot.mkdir(exist_ok=False)
    pilot_cases=[material('P01','pilot_standard_rail','南京','2026-11-15','2026-11-16','2026-11-20','260.00',[
        item('P01-T','transit','260.00','2026-11-15',route='常州至南京',seat_class='高铁二等座')],passed('v2','no_issues_found',[],'260.00')),
        material('P02','pilot_csv_date_gate','南昌','2026-11-20','2026-11-21','2026-11-25','220.00',[
        item('P02-T','transit','220.00','2026-11-19',route='九江至南昌',seat_class='高铁二等座')],
        dict(validation_status='needs_manual_review',required_issue_codes=['CSV_DATE_CONFLICT'],application_created=False))]
    pilot_gold={c['id']:dict(kind='material',**c.pop('expected')) for c in pilot_cases}
    dump(pilot/'materials.inputs.json',pilot_cases);dump(pilot/'qa.inputs.json',[]);dump(pilot/'gold.json',pilot_gold)
    print('Created 8 QA + 8 material reserve candidates, and 2 separate development pilot cases. No model calls.')


if __name__=='__main__':build()
