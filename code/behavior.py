import copy
import demo3
import demo4
import pm4py
import pandas as pd
from pm4py.objects.petri_net.importer import importer as pnml_importer
from pm4py.algo.simulation.playout.petri_net import algorithm as simulator
#导入模型
net, initial_marking, final_marking=pnml_importer.apply('Dataset/thesis.pnml')
#读取所有日志
dataframe = pd.read_csv('Dataset/thesis1.csv', sep=',')
dataframe = pm4py.format_dataframe(dataframe, case_id='case', activity_key='Activity', timestamp_key='startTime')
log = pm4py.convert_to_event_log(dataframe)
aligned_traces = pm4py.conformance_diagnostics_alignments(log, net, initial_marking, final_marking)
for j in aligned_traces:
    j=demo4.reverse_result(j['alignment'])
# for i in aligned_traces:
#     print(i)
# for i in range(len(aligned_traces)):
#     if aligned_traces[i]['fitness']!=1.0:
#         print(aligned_traces[i])
#         print(log[i])
#         print('**********')
# demo3.add(aligned_traces,log)
# demo3.lack(aligned_traces,log)
# demo3.repeat(aligned_traces)
# demo3.replace1(aligned_traces)
# demo3.replace2(aligned_traces,log)


attribute_name=['org:resource','fixedCost']#属性列表自定义

#计算每个事例中事件的个数
single_event_count=[]#创建列表，保存每个事例中事件的个数
for i in log:
    single_event_count.append(len(i))

legal_log_sequence=[]#合规事例序号
no_legal_log_sequence=[]#不合规事例序号
aligned_traces_item=0
while aligned_traces_item<len(aligned_traces):
    if aligned_traces[aligned_traces_item]['fitness']==1.0:
        legal_log_sequence.append(aligned_traces_item)
    else:
        no_legal_log_sequence.append(aligned_traces_item)
    aligned_traces_item+=1

#构造所有合法属性值集合
legal_attribute_dic={}
for item in attribute_name:
    legal_attribute_dic[item]=[]

#创建合法、非法日志集，合法236
legal_log=[]
no_legal_log=[]
log_count=len(single_event_count)#事例个数
log_record_count=0
while log_record_count<log_count:#遍历合规性检查结果，依据fitness值判定合法日志
    if aligned_traces[log_record_count]['fitness']==1.0:
        legal_log.append(log[log_record_count])
    else:
        no_legal_log.append(log[log_record_count])
    log_record_count+=1
for attribute in attribute_name:
    for legal_log_item in legal_log:
        for item in legal_log_item:
            legal_attribute_dic[attribute].append(item[attribute])
#合法属性值集合去重
for item in legal_attribute_dic:
    legal_attribute_dic[item]=list(set(legal_attribute_dic[item]))

#找出异常点、属性、属性值
deficiency_list=[]#记录不予分析的异常
result=[]#存储异常点、属性、属性值三元组
record_count=0#标记第几个trace
all_sextuple_list=[]#用于存放所有的六元组
no_legal_active_dic={}#不合规行为及其影响案例数
while record_count<len(log):#所有trace逐个遍历
    if aligned_traces[record_count]['fitness'] != 1.0:  # 仅对不合规流程进行检查
        # print(record_count)
        pre_event_str= ''#记录前一个事件
        # exception_list1=[]#存放异常类别
        # exception_list2=[]#处理替换异常
        event_index=0#记录当前log中第几个事件
        buffer_set=[]#缓冲
        log_count=0
        temp=aligned_traces[record_count]['alignment']
        for alignment_item_number in range(len(temp)):#对单个trace的alignment的对比结果进行遍历
            exception_list1 = []  # 存放异常类别
            exception_list2 = []  # 处理替换异常
            # print(alignment_item)
            # print(buffer_set)
            exception_mark = 0  # 默认无异常
            sextuple_list = []  # 存储该异常行为中的所有六元组
            if '>>' in str(temp[alignment_item_number]) and len(buffer_set)!=0:
                similar_exception_list=[]#存放同一种异常行为
                if temp[alignment_item_number][0]=='>>' and temp[alignment_item_number][1]==None:#不可见变迁
                    pass
                elif temp[alignment_item_number][0]=='>>' and temp[alignment_item_number][1]!='>>':#>>,b
                    exception_mark=1#发生异常
                    # if len(buffer_set)==0:#>>,b 开始就缺少，不予考虑
                    #     buffer_set.append(alignment_item)
                    #     deficiency_list.append('缺失起始事件'+str(alignment_item[1]))
                    #     exception_mark = 0

                    if buffer_set[-1][0] == buffer_set[-1][1]:  # a,a >>,b  缺少执行
                        if alignment_item_number+1<(len(temp)-1) and temp[alignment_item_number+1][1]=='>>':#当前为事件替换的前一个
                            exception_mark=0
                        exception_list1.append(buffer_set[-1])
                        exception_list1.append(temp[alignment_item_number])
                        pre_event_str=str(buffer_set[-1][0])+'后面缺少执行'+str(temp[alignment_item_number][1])
                        i=0
                        while i <len(aligned_traces):
                            index=0
                            mark=0
                            for j in aligned_traces[i]['alignment']:
                                if mark==0:
                                    x=[]#异常行为放在一起
                                    if j==exception_list1[0]:
                                        mark=1
                                        # similar_exception_list.append(log[i][index])
                                        x.append(log[i][index])
                                else:
                                    if j==exception_list1[1]:
                                        mark=0
                                        similar_exception_list.append(x)
                                    else:
                                        mark=0
                                        # similar_exception_list.pop()
                                if j[0]!='>>':
                                    index+=1
                            i+=1
                        for i in attribute_name:
                            abnormal_source=log[record_count][log_count-1][i]#异常根源
                            impact_case=0
                            for j in similar_exception_list:
                                for k in j:
                                    if k[i]==abnormal_source:
                                        impact_case+=1
                                        break
                            sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])#属性，异常根源，影响案例数，影响强度，共性相关性，异常点
                        buffer_set.append(temp[alignment_item_number])
                    elif buffer_set[-1][0]=='>>' and buffer_set[-1][1]!='>>':#>>,a >>,b 都没执行，不予考虑
                        exception_mark = 0
                        deficiency_list.append('缺少执行'+str(temp[alignment_item_number][1]))
                        buffer_set.append(temp[alignment_item_number])
                    elif buffer_set[-1][0]!='>>' and buffer_set[-1][1]=='>>':#a,>> >>,b 替换
                        # print('************')
                        # print(buffer_set[-1])
                        # print(temp[alignment_item_number])
                        exception_mark = 1  # 发生异常
                        exception_list1.append(buffer_set[-1])#a,>> >>,b
                        exception_list1.append(temp[alignment_item_number])
                        exception_list2.append(temp[alignment_item_number])#>>,b a,>>
                        exception_list2.append(buffer_set[-1])
                        pre_event_str=str(temp[alignment_item_number][1])+'被'+str(buffer_set[-1][0]+'替换')
                        i=0
                        while i<len(aligned_traces):
                            index=0
                            mark=0
                            for j in aligned_traces[i]['alignment']:
                                if mark==0:
                                    x=[]
                                    y=[]
                                    if j==exception_list1[0]:
                                        mark=1
                                        # similar_exception_list.append(log[i][index])
                                        x.append(log[i][index])
                                    elif j==exception_list2[0]:
                                        mark=2
                                        # similar_exception_list.append(log[i][index])
                                        # y.append(log[i][index])
                                elif mark==1:
                                    if j==exception_list1[1]:
                                        similar_exception_list.append(x)
                                        mark=0
                                    elif j!=exception_list1[1]:
                                        mark=0
                                        # similar_exception_list.pop()
                                elif mark==2:
                                    if j==exception_list2[1]:
                                        mark=0
                                        y.append(log[i][index])
                                        similar_exception_list.append(y)
                                    elif j!=exception_list2[1]:
                                        mark=0
                                        # similar_exception_list.pop()
                                if j[0]!='>>':
                                    index+=1
                            i+=1
                        for i in attribute_name:
                            abnormal_source=log[record_count][log_count-1][i]
                            impact_case=0
                            for j in similar_exception_list:
                                for k in j:
                                    if k[i]==abnormal_source:
                                        impact_case+=1
                                        break
                            sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                            # print(sextuple_list[-1])
                        buffer_set.append(temp[alignment_item_number])

                elif temp[alignment_item_number][1]=='>>' and temp[alignment_item_number][0]!='>>':#b,>>
                    exception_mark = 1#发生异常
                    if buffer_set[-1][0]==buffer_set[-1][1]:#a,a b,>>  额外执行
                        if alignment_item_number+1<(len(temp)-1) and temp[alignment_item_number+1][0]=='>>':#当前事件为替换的前一个
                            # print('****')
                            exception_mark=0
                        exception_list1.append(buffer_set[-1])
                        exception_list1.append(temp[alignment_item_number])
                        if str(buffer_set[-1][0])==str(temp[alignment_item_number][0]):
                            pre_event_str=str(buffer_set[-1][0])+'后面重复执行'+str(temp[alignment_item_number][0])
                        else:
                            pre_event_str=str(buffer_set[-1][0])+'后面额外执行'+str(temp[alignment_item_number][0])
                        i=0
                        while i<len(aligned_traces):
                            index=0
                            mark=0#标记第一个是否对应
                            for j in aligned_traces[i]['alignment']:
                                if mark==0:
                                    x=[]
                                    if j==exception_list1[0]:
                                        mark=1
                                        x.append(log[i][index])
                                        # similar_exception_list.append()#添加异常行为的事件(本质是添加属性值列表)
                                else:#看第二个能否对应
                                    if j==exception_list1[1]:
                                        mark=0
                                        x.append(log[i][index])
                                        similar_exception_list.append(x)#添加异常行为的事件(本质是添加属性值列表)
                                    else:
                                        mark=0
                                        # similar_exception_list.pop()#第一个对应而第二个没有对应则删除刚才添加的“第一个”事件
                                if j[0]!='>>':
                                    index+=1
                            i+=1
                        no_attribute=[]
                        for i in attribute_name:
                            if log[record_count][log_count-1][i]==log[record_count][log_count][i]:
                                no_attribute.append(i)
                        for i in attribute_name:
                            abnormal_source=log[record_count][log_count-1][i]
                            impact_case=0
                            for j in similar_exception_list:
                                for k in j:
                                    if k[i]==abnormal_source:
                                        impact_case+=1
                                        break
                            sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        for i in attribute_name:
                            if i not in no_attribute:
                                abnormal_source=log[record_count][log_count][i]
                                impact_case=0
                                for j in similar_exception_list:
                                    for k in j:
                                        if k[i]==abnormal_source:
                                            impact_case+=1
                                            break
                                sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        buffer_set.append(temp[alignment_item_number])
                    elif buffer_set[-1][0]=='>>' and buffer_set[-1][1]!='>>':#>>,a b,>> 替换
                        exception_mark = 1  # 发生异常
                        #两个list中存的都是ab替换的异常行为
                        exception_list1.append(buffer_set[-1])#>>,a b,>>
                        exception_list1.append(temp[alignment_item_number])
                        exception_list2.append(temp[alignment_item_number])#b,>> >>,a
                        exception_list2.append(buffer_set[-1])
                        pre_event_str=str(buffer_set[-1][1])+'被'+str(temp[alignment_item_number][0]+'替换')
                        i=0
                        while i<len(aligned_traces):
                            index=0
                            mark=0
                            for j in aligned_traces[i]['alignment']:
                                if mark==0:
                                    x=[]
                                    y=[]
                                    if j==exception_list1[0]:
                                        mark=1
                                        # similar_exception_list.append(log[i][index])
                                    elif j==exception_list2[0]:
                                        mark=2
                                        # similar_exception_list.append()
                                        y.append(log[i][index])
                                elif mark==1:
                                    if j==exception_list1[1]:
                                        x.append(log[i][index])
                                        similar_exception_list.append(x)
                                        mark=0
                                    elif j!=exception_list1[1]:
                                        mark=0
                                        # similar_exception_list.pop()
                                elif mark==2:
                                    if j==exception_list2[1]:
                                        mark=0
                                        similar_exception_list.append(y)
                                    elif j!=exception_list2[1]:
                                        mark=0
                                        # similar_exception_list.pop()
                                if j[0]!='>>':
                                    index+=1
                            i+=1
                        for i in attribute_name:
                            abnormal_source=log[record_count][log_count][i]
                            impact_case=0
                            for j in similar_exception_list:
                                for k in j:
                                    if k[i]==abnormal_source:
                                        impact_case+=1
                                        break
                            sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        buffer_set.append(temp[alignment_item_number])
                    elif buffer_set[-1][0]!='>>' and buffer_set[-1][1]=='>>' and buffer_set[-1][0]!=temp[alignment_item_number][0]:#a,>> b,>> 额外执行
                        exception_mark = 1  # 发生异常
                        exception_list1.append(buffer_set[-1])
                        exception_list1.append(temp[alignment_item_number])
                        pre_event_str='执行添加事件'+str(temp[alignment_item_number][0])
                        i=0
                        while i<len(aligned_traces):
                            index=0
                            mark=0
                            for j in aligned_traces[i]['alignment']:
                                if mark==0:
                                    x=[]
                                    if j==exception_list1[0]:
                                        mark=1
                                        x.append(log[i][index])
                                        # similar_exception_list.append()
                                else:
                                    if j==exception_list1[1]:
                                        mark=0
                                        x.append(log[i][index])
                                        similar_exception_list.append(x)
                                    else:
                                        mark=0
                                        # similar_exception_list.pop()
                                if j[0]!='>>':
                                    index+=1
                            i+=1
                        no_attribute=[]
                        for i in attribute_name:
                            if log[record_count][log_count-1][i]==log[record_count][log_count][i]:
                                no_attribute.append(i)
                        for i in attribute_name:
                            abnormal_source=log[record_count][log_count-1][i]
                            impact_case=0
                            for j in similar_exception_list:
                                for k in j:
                                    if k[i]==abnormal_source:
                                        impact_case+=1
                                        break
                            sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        for i in attribute_name:
                            if i not in no_attribute:
                                abnormal_source=log[record_count][log_count][i]
                                impact_case=0
                                for j in similar_exception_list:
                                    for k in j:
                                        if k[i]==abnormal_source:
                                            impact_case+=1
                                            break
                                sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        buffer_set.append(temp[alignment_item_number])
                    elif buffer_set[-1]==temp[alignment_item_number]:#a,a b,>> b,>>,c,c 重复执行
                        exception_mark = 1  # 发生异常
                        exception_list1.append(buffer_set[-1])
                        exception_list1.append(temp[alignment_item_number])
                        pre_event_str=str(temp[alignment_item_number][0])+'重复执行'
                        i=0
                        while i<len(aligned_traces):
                            index=0
                            mark=0
                            for j in aligned_traces[i]['alignment']:
                                if mark==0:
                                    x=[]
                                    if j==exception_list1[0]:
                                        mark=1
                                        x.append(log[i][index])
                                        # similar_exception_list.append()
                                    else:
                                        if j==exception_list1[1]:
                                            mark=0
                                            x.append(log[i][index])
                                            similar_exception_list.append(x)
                                        else:
                                            mark=0
                                            # similar_exception_list.pop()
                                    if j[0]!='>>':
                                        index+=1
                            i+=1
                        no_attribute=[]
                        for i in attribute_name:
                            if log[record_count][log_count-1][i]==log[record_count][log_count][i]:
                                no_attribute.append(i)
                        for i in attribute_name:
                            abnormal_source=log[record_count][log_count-1][i]
                            impact_case=0
                            for j in similar_exception_list:
                                for k in j:
                                    if k[i]==abnormal_source:
                                        impact_case+=1
                                        break
                            sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        for i in attribute_name:
                            if i not in no_attribute:
                                abnormal_source=log[record_count][log_count][i]
                                impact_case=0
                                for j in similar_exception_list:
                                    for k in j:
                                        if k[i]==abnormal_source:
                                            impact_case+=1
                                            break
                                sextuple_list.append([i,abnormal_source,impact_case,0,0,pre_event_str])
                        buffer_set.append(temp[alignment_item_number])
            elif len(buffer_set) == 0 and '>>' in str(temp[alignment_item_number]):
                if temp[alignment_item_number][0]!='>>' and temp[alignment_item_number][1]=='>>':# b,>> 开始就异常
                    exception_mark=1
                    similar_exception_list=[]
                    exception_list1.append(temp[alignment_item_number])
                    pre_event_str = '起始事件不应该是' + str(temp[alignment_item_number][0])
                    if alignment_item_number+1<(len(temp)-1) and temp[alignment_item_number+1][0]=='>>':
                        pre_event_str='起始事件不应该是' + str(temp[alignment_item_number][0])+'而是事件'+str(temp[alignment_item_number+1][0])
                        exception_mark=0
                    i = 0
                    while i < len(aligned_traces):
                        x = []
                        if exception_list1[0] == aligned_traces[i]['alignment'][0]:
                            x.append(log[i][0])
                            similar_exception_list.append(x)
                        i+=1
                    for i in attribute_name:
                        abnormal_source = log[record_count][log_count][i]
                        impact_case = 0
                        for j in similar_exception_list:
                            for k in j:
                                if k[i] == abnormal_source:
                                    impact_case += 1
                                    break
                        sextuple_list.append([i, abnormal_source, impact_case, 0, 0, pre_event_str])
                    buffer_set.append(temp[alignment_item_number])
                elif temp[alignment_item_number][0]=='>>' and temp[alignment_item_number][1]!='>>':# >>,b 开始就异常
                    exception_mark=1
                    if alignment_item_number+1<(len(temp)-1) and temp[alignment_item_number+1][1]=='>>':
                        exception_mark=0
                    buffer_set.append(temp[alignment_item_number])
                    deficiency_list.append('缺失起始事件'+str(temp[alignment_item_number][1]))
                    exception_mark=0
            elif '>>' not in str(temp[alignment_item_number]):
                buffer_set.append(temp[alignment_item_number])
            if temp[alignment_item_number][0]!='>>':
                log_count+=1
            # print(exception_mark)
            if exception_mark==1:#有异常发生，计算值
                if len(exception_list1)==1:
                    no_legal_active_dic_key=str(exception_list1[0])
                elif len(exception_list1)==2:
                    no_legal_active_dic_key = str(exception_list1[0]) + ',' + str(exception_list1[1])#异常行为列表转str
                if no_legal_active_dic_key not in list(no_legal_active_dic):#字典中没有该异常行为则添加
                    no_legal_active_dic[no_legal_active_dic_key]=[]
                    while sextuple_list:
                        sextuple=sextuple_list.pop()
                        no_legal_active_dic[no_legal_active_dic_key].append(sextuple)
                        all_sextuple_list.append(sextuple)
                else:
                    while sextuple_list:
                        sextuple=sextuple_list.pop()
                        no_legal_active_dic[no_legal_active_dic_key].append(sextuple)#字典中已有该异常行为则直接添加六元组
                        all_sextuple_list.append(sextuple)
                if len(exception_list2)==1:
                    no_legal_active_dic_key=str(exception_list2[0])
                elif len(exception_list2)==2:
                    no_legal_active_dic_key = str(exception_list2[0]) + ',' + str(exception_list2[1])#异常行为列表转str
                if no_legal_active_dic_key not in list(no_legal_active_dic) and no_legal_active_dic_key!='':
                    no_legal_active_dic[no_legal_active_dic_key]=[]#字典中没有该异常行为则添加
                    while sextuple_list:
                        sextuple=sextuple_list.pop()
                        no_legal_active_dic[no_legal_active_dic_key].append(sextuple)
                        all_sextuple_list.append(sextuple)
                elif no_legal_active_dic_key in list(no_legal_active_dic) and no_legal_active_dic_key!='':
                    while sextuple_list:
                        sextuple=sextuple_list.pop()
                        no_legal_active_dic[no_legal_active_dic_key].append(sextuple)
                        all_sextuple_list.append(sextuple)
                exception_list1=[]#异常行为清空
                exception_list2=[]
                similar_exception_list=[]
    record_count+=1
#筛选异常根源
for i in list(no_legal_active_dic):#i为异常行为key.
    a=[]
    for j1 in no_legal_active_dic[i]:#j1为异常行为的四元组列表的子四元组value
        # print(k)
        not_attribute_str=j1[0]#获取属性
        not_attribute=j1[1]#异常根源
        not_attribute_str_sum=0#计算在不合规行为中出现的次数
        attribute_str_sum=0#计算行为中出现的次数
        for k1 in no_legal_active_dic[i]:#遍历同一异常行为中的四元组，查看同一属性下的属性值是否有相同的
            if k1[0]==not_attribute_str:
                if k1[1]==not_attribute:
                    not_attribute_str_sum+=1
        for k2 in log:#基于所有日志
            for j2 in k2:
                if j2[not_attribute_str]==not_attribute:
                    attribute_str_sum+=1
        if attribute_str_sum==0:
            rate=99999
        else:
            rate=round(not_attribute_str_sum/attribute_str_sum,3)#影响强度
        j1[3]=rate
        if rate>=0.01:
            a.append(j1)
    if len(a)!=0:
        no_legal_active_dic[i]=a
    else:
        del no_legal_active_dic[i]


#共性相关性计算
for i in list(no_legal_active_dic):#基于异常行为范围中
    for j in no_legal_active_dic[i]:
        t=0
        t_key=j[0]
        t_value=j[1]
        t_value=j[1]
        for k in list(no_legal_active_dic):
            for l in no_legal_active_dic[k]:
                if l[0]==t_key:
                    if l[1]==t_value:
                        t+=1
                        # break
        j[4]=t

#排序
#C：根据所有属性中影响案例数的最大值对不合规行为进行排序。
sequence_dic=copy.deepcopy(no_legal_active_dic)#深拷贝
for i in list(sequence_dic):
    a=[]
    for j in sequence_dic[i]:
        a.append(j[2])
    sequence_dic[i]=max(a)
sequence_list = sorted(sequence_dic.items(), key=lambda x: x[1], reverse=True)#对不合规行为进行排序
new_no_legal_active_dic={}
for i in sequence_list:#不合规行为序列且附带四元组
    new_no_legal_active_dic[i[0]]=no_legal_active_dic[i[0]]

#B：根据所有四元组中影响案例数的最大值对异常根源所属属性进行排序

attribute_sequence_dic={}#影响案例数集合
for i in attribute_name:
    attribute_sequence_dic[i]=[]

for i in all_sextuple_list:
    # if i[0] not in list(attribute_sequence_dic):
    #     attribute_sequence_dic[i[0]]=[i[2]]
    # elif i[0] in list(attribute_sequence_dic):
    attribute_sequence_dic[i[0]].append(i[2])

for i in list(attribute_sequence_dic):
    attribute_sequence_dic[i]=max(attribute_sequence_dic[i])
attribute_sequence_list=sorted(attribute_sequence_dic.items(), key=lambda x: x[1], reverse=True)#对属性值进行排序
# print(attribute_sequence_list)
attribute_sequence_list_name=[]
for i in attribute_sequence_list:#属性优先级
    attribute_sequence_list_name.append(i[0])

#A：根据每个异常根源的    共性   相关性对所属属性的异常根源属性值列表进行排序;
print('*********************************************流程异常的原因序列********************************************')
print()
print('                 异常点                                   属性              不合法属性值')
for i in list(new_no_legal_active_dic):
    print('--------------------------------------------------------------------------------------------------------')
    flag=1
    exception_len=0
    for j in attribute_sequence_list_name:
        a=[]
        for k in no_legal_active_dic[i]:
            if k[0]==j:
                a.append(k)
        english_len=0
        Chinese_len=0
        if a!=[]:
            for k in a[0][-1]:#统计异常点中汉字和英文字符的个数
                if k>='a' and k<='z' or k>='A' and k<='Z':
                    english_len+=1
            Chinese_len=len(a[0][-1])-english_len
            if exception_len==0:
                print(a[0][-1],end='')#打印异常点
                y=0
                while y<55-(Chinese_len*1.5+english_len):
                    print(' ', end='')
                    y += 1
                exception_len=len(a[0][-1])
            elif exception_len!=0:
                y=0
                while y<55:
                    print(' ',end='')
                    y+=1
            exception_len = len(a[0][-1])
            print(j,end='')
            y=0
            while y<20-len(j):
                print(' ',end='')
                y+=1
            a2=[]
            for k in a:
                mark=1
                for k2 in a2:
                    if k ==k2:
                        mark=0
                if mark==1:
                    a2.append(k)
            b=sorted(a2,key=lambda x:x[4],reverse=True)
            x=0
            while x <len(b):
                print(b[x][1],end='')
                if x!=len(b)-1:
                    print(end='、')
                else:
                    print()
                x+=1
for i in list(set(deficiency_list)):
    print('--------------------------------------------------------------------------------------------------------')
    print(i,end='                          ')
    print('               条件不足暂不分析原因')

# print()
# print()
# print('*********************************************异常行为的原因序列********************************************')
# print()
# print('                 异常点                                   属性              不合法属性值')
# # print('异常行为分析')
# #属性、属性值排
# for i in list(new_no_legal_active_dic):#i为异常行为
#     single_active_attribute={}
#     #对单个异常行为中的属性排序
#     for j in new_no_legal_active_dic[i]:#j为元组
#         if j[0] not in list(single_active_attribute):
#             single_active_attribute[j[0]]=[j[2]]
#         else:
#             single_active_attribute[j[0]].append(j[2])
#     for j1 in list(single_active_attribute):
#         single_active_attribute[j1]=max(single_active_attribute[j1])
#
#     single_active_attribute_list=sorted(single_active_attribute.items(), key=lambda x: x[1], reverse=True)#对属性进行排序  [('Resource', 3), ('Costs', 3)]
#     flag=1
    # print('--------------------------------------------------------------------------------------------------------')
    # print('属性与属性值综合分析')
    # for l in single_active_attribute_list:
    #
    #     a=[]
    #     for k1 in new_no_legal_active_dic[i]:
    #         if k1[0]==l[0]:
    #             a.append(k1)
    #     a2=[]
    #     for k in a:
    #         mark=1
    #         for k2 in a2:
    #             if k==k2:
    #                 mark=0
    #         if mark==1:
    #             a2.append(k)
    #     sorted_lst = sorted(a2, key=lambda x: (x[3], x[4]), reverse=True)
    #     if flag==1:
    #         print(sorted_lst[0][-1],end='')#打印异常点
    #         english_len=0
    #         Chinese_len=0
    #         for k3 in sorted_lst[0][-1]:
    #             if k3 >= 'a' and k3 <= 'z' or k3 >= 'A' and k3 <= 'Z':
    #                 english_len += 1
    #         Chinese_len = len(a[0][-1]) - english_len
    #         y=0
    #         while y<55-(Chinese_len*1.5+english_len):
    #             print(' ',end='')
    #             y+=1
    #         flag=0
    #     else:
    #         y=0
    #         while y<55:
    #             print(' ',end='')
    #             y+=1
    #     print(l[0],end='')
    #     y=0
    #     while y<20-len(j):
    #         print(' ',end='')
    #         y+=1
    #     x=0
    #     while x<len(sorted_lst):
    #         if x!=len(sorted_lst)-1:
    #             print(sorted_lst[x][1],end='、')
    #         else:
    #             print(sorted_lst[x][1])
    #         x+=1
    #
    # tuple_list= sorted(new_no_legal_active_dic[i], key=lambda x: (x[3], x[4]), reverse=True)
    # tuple_list2=[]
    # for k4 in tuple_list:
    #     mark=1
    #     for k5 in tuple_list2:
    #         if k4==k5:
    #             mark=0
    #     if mark==1:
    #         tuple_list2.append(k4)
    # print('依据属性值的相关性分析')
    # print(tuple_list2[0][-1],end='')
    # y=0
    # while y<55-len(tuple_list2[0][-1]):
    #     print(' ',end='')
    #     y+=1
    # y=0
    # for x in tuple_list2:
    #     if y==0:
    #         print(x[0],end='')
    #         z=0
    #         while z<20-len(x[0]):
    #             print(' ',end='')
    #             z+=1
    #         print(x[1])
    #     else:
    #         z=0
    #         while z<55:
    #             print(' ',end='')
    #             z+=1
    #         print(x[0], end='')
    #         z = 0
    #         while z < 20 - len(x[0]):
    #             print(' ', end='')
    #             z += 1
    #         print(x[1])
    #     y+=1
# print(all_sextuple_list)
# b={'执行添加事件Check wire in long axis':[],'Remove trocar后面额外执行Check wire in short axis':[],'Prepare implements被Get in sterile clothes替换':[]}
# c={'R_32_1H':[],'R_48_2D':[],'R_45_2A':[],'R_13_1C':[],'R_46_2B':[],'R_47_2C':[]}
# for i in all_sextuple_list:
#     if i[-1]=='Prepare implements被Get in sterile clothes替换':
#         c[i[1]].append(i[-2])
# print(c)