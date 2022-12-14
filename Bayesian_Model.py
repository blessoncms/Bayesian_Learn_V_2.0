from sklearn.model_selection import train_test_split
from multiprocessing import Pool, cpu_count
from itertools import repeat,cycle,islice
import pandas as pd
import numpy as np
from itertools import chain


def Series_to_Dict(Series_Data):
    Dict_Data={k[0]:v for k,v in Series_Data.items()}
    return Dict_Data

class Bayesian_Model_Training_and_Testing:
	def __init__(self,Data_X,Data_Y,Resolution,Number_of_Feature_Connections,alpha):
		self.Resolution=Resolution
		self.Number_of_Feature_Connections=Number_of_Feature_Connections
		self.alpha=alpha
		self.Min_Prior_Prob=1
		self.Missing_Connection_Prior_Prob=0.001
		self.Missing_Connection_Weights=0.001
		self.Prob_Cor_Fact=0.00001
		self.Key_Width=4

#Find the basic parameters
		df_Data_X=pd.DataFrame(Data_X)
		df_Data_Y=pd.DataFrame(Data_Y) 

		df_Data_Y.set_axis(['Class'], axis='columns', inplace=True)
		self.Unique_Class_Names =df_Data_Y.Actual_Class.unique() 
		self.Unique_Class_Names.sort()
        
		self.Number_of_Class=len(self.Unique_Class_Names)
		self.Total_Number_of_Objects=df_Data_X.shape[0]
		self.Number_of_Features=len(df_Data_X.columns)
		self.Min_Feature_Values=df_Data_X.min()
		self.Max_Feature_Values=df_Data_X.max()
		self.Object_Min_Prob=1/(self.Number_of_Class**4)
		Temp_df_Data_X=(((df_Data_X-self.Min_Feature_Values)/(self.Max_Feature_Values-self.Min_Feature_Values))*(self.Resolution-1)).round(0)
		self.df_Train_Data_XY=Temp_df_Data_X.copy()
		self.df_Train_Data_XY.insert(0,'Class',df_Data_Y.values)
		self.df_Train_Data_XY.reset_index(drop=True,inplace=True)
        
		del df_Data_X,df_Data_Y,Temp_df_Data_X

#Seting Connection pattern
		Features_list=[i for i in range(self.Number_of_Features)]
		bb=[]
		for i in range(self.Number_of_Feature_Connections):
			if i==0:
				bb.append(Features_list)
			else:
				bb.append(islice(cycle(Features_list), i, None))
		self.Connection_Pattern=tuple(zip(*bb)) 

#Prediction Report Columns Names
		CFL=['Index','ACL','ACP','PCL','PCP','CF']
		PCOL=[('PCO_'+str(i+1)) for i in range(0,self.Number_of_Class)]
		ProbL=[('Prob_PCO_'+str(i+1)) for i in range(0,self.Number_of_Class)]
		DataL=[('FV_'+str(i+1)) for i in range(0,self.Number_of_Features)]
		self.Prediction_Report_Columns_List=CFL+PCOL+ProbL+DataL

	def Obtain_Connection_Keys_for_a_Single_Object(self,Object_Data): 
		Object_Data=list(Object_Data)
		Actual_Class=Object_Data.pop(0)
		Connection_Key_List=[]   
		for Ctn in self.Connection_Pattern:   
			Connection_Key=[str(int(j)).zfill(self.Key_Width)+"-"+str(int(Object_Data[j])).zfill(self.Key_Width) for j in Ctn]
			Connection_Key.insert(0,str(int(Actual_Class)).zfill(self.Key_Width))
			Connection_Key_List.append("*".join(Connection_Key))
			del Connection_Key 
		return Connection_Key_List  

	def Create_Connection_Weights_for_Training_Data_Set(self):
		dict_Connection_Weights=self.df_Train_Data_XY.apply(self.Obtain_Connection_Keys_for_a_Single_Object,axis=1)
		dict_Connection_Weight_List=list(chain.from_iterable(list(dict_Connection_Weights)))
		Temp=pd.DataFrame(dict_Connection_Weight_List)
		self.Orginal_Connection_Weights=Series_to_Dict(Temp.value_counts())

#Blesson
	def Temp_Fun_1(self,x): # only for Create_Normalized_Connection_Weights()
		return self.Orginal_Connection_Weights[x]

	def Temp_Fun_2(self,x): # only for Create_Normalized_Connection_Weights()
		exist_class=[]
		[exist_class.append((str(int(c)).zfill(self.Key_Width)+'*'+x))for c in self.Unique_Class_Names if ((str(int(c)).zfill(self.Key_Width)+'*'+x)  in self.Orginal_Connection_Weights.keys())]
		bb=sum(list(map(self.Temp_Fun_1,exist_class)))
		return dict((x,self.Orginal_Connection_Weights[x]/bb) for x in exist_class)

	def Normalize_Connection_Weights_and_Initialize_Prior_Probabilities(self):
		list_keys=list(self.Orginal_Connection_Weights.keys())
		uniq_conn_wt=np.unique([x[5:] for x in list_keys])
		Norm_Conn_wts=[]
		[Norm_Conn_wts.append(self.Temp_Fun_2(x)) for x in uniq_conn_wt]
		self.Connection_Weights= {k: v for d in Norm_Conn_wts for k, v in d.items()}  
		self.Prior_Probabilities={key: self.Min_Prior_Prob for key in self.Connection_Weights.keys()} 
##
	def Find_Object_Likelihood_for_the_Given_Class_for_an_Object(self,Object_Data):# for any given object data set 
		Keys=self.Obtain_Connection_Keys_for_a_Single_Object(Object_Data)
		Prior_for_the_object=[self.Prior_Probabilities[k] if  k in self.Prior_Probabilities else self.Missing_Connection_Prior_Prob for k in Keys]
		Connection_Weights_for_the_object=[self.Connection_Weights[k] if  k in self.Connection_Weights else self.Missing_Connection_Weights for k in Keys]
		Object_Likelihood_for_the_Given_Class=np.prod(np.array(Prior_for_the_object)*np.array(Connection_Weights_for_the_object),dtype=np.float128)
		return Object_Likelihood_for_the_Given_Class

	def Find_Object_Likelihood_for_All_Class_for_an_Object(self,Object_Data):
		Temp_Object_Data=[[self.Unique_Class_Names[c]]+list(Object_Data) for c in range(0,self.Number_of_Class)]
		Temp_Object_Probability=[self.Find_Object_Likelihood_for_the_Given_Class_for_an_Object(Temp_Object_Data[c]) for c in range(0,self.Number_of_Class)] 
		if(sum(Temp_Object_Probability)==0):
			Temp_Object_Probability=[self.Object_Min_Prob for Value in Temp_Object_Probability]
		Temp_Object_Probability=[np.float128(Value/(sum(Temp_Object_Probability))) for Value in Temp_Object_Probability]
		Temp_list=list(np.argsort(Temp_Object_Probability))
		Temp_list.reverse()
		Predection_Class_Order=[self.Unique_Class_Names[int(Temp_list[j])]  for j in range(0,self.Number_of_Class)]
		Object_Probability=[Temp_Object_Probability[int(Temp_list[j])]  for j in range(0,self.Number_of_Class)]
		return [Predection_Class_Order,Object_Probability]

	def Object_Likelihood_Report(self,Object_Data):
		Index=Object_Data.name
		Object_Data=list(Object_Data)
		Actual_Class=int(Object_Data.pop(0))
		Temp_Var=self.Find_Object_Likelihood_for_All_Class_for_an_Object(Object_Data)
		Predection_Class_Order=Temp_Var[0]
		Object_Probability=Temp_Var[1]
		Actual_Class_Index=int(np.where(np.array(Predection_Class_Order)==Actual_Class)[0])
		Predicted_Class=Predection_Class_Order[0]
		Predicted_Class_Probability=Object_Probability[0]
		Actual_Class_Probability=Object_Probability[Actual_Class_Index]  
 
		if(Actual_Class==Predicted_Class):
			Correction_Factor=np.NaN;
		else:
			Correction_Factor=(1-(Actual_Class_Probability/(Predicted_Class_Probability+self.Prob_Cor_Fact**2)))
 
		Predicted_Report=[Index,Actual_Class,Actual_Class_Probability,Predicted_Class,Predicted_Class_Probability,Correction_Factor]
		Predection_Data=Predicted_Report+Predection_Class_Order+Object_Probability+Object_Data
		return Predection_Data


	def Prediction_Report_for_N_Data_Set(self,df_Data_set): 
		Prediction=df_Data_set.apply(self.Object_Likelihood_Report,axis=1)
		Prediction_Report=pd.DataFrame(list(Prediction),columns=self.Prediction_Report_Columns_List)
		return Prediction_Report.set_index('Index')


#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
	def Create_the_Structure_of_the_Model(self):
		self.Create_Connection_Weights_for_Training_Data_Set()
		self.Normalize_Connection_Weights_and_Initialize_Prior_Probabilities()
		Train_Prediction_Report=self.Prediction_Report_for_N_Data_Set(self.df_Train_Data_XY)
		Table_For_Data_Updation=Train_Prediction_Report.dropna()
		return Table_For_Data_Updation

	def Testing_the_Model(self,Feature_Data_Set):
		Test_Prediction_Report=self.Prediction_Report_for_N_Data_Set(Feature_Data_Set)
		Table_For_Data_Updation=Test_Prediction_Report.dropna()
		return Table_For_Data_Updation

#Updation
	def Update_Prior_Probabilities_for_the_Given_Object(self,Object_Data): #Update Prior Probabilities
		Object_Data=list(Object_Data)
		Actual_Class=Object_Data[0]
		FVL=Object_Data[(5+2*self.Number_of_Class):(5+2*self.Number_of_Class+self.Number_of_Features)]# Feature values for the object   
		Key_List_For_Updation=self.Obtain_Connection_Keys_for_a_Single_Object([Actual_Class]+FVL)
		for i in range(0,len(Key_List_For_Updation)):
			try:
				self.Prior_Probabilities[Key_List_For_Updation[i]]+=self.alpha*Object_Data[4] 
			except:
				self.Prior_Probabilities[Key_List_For_Updation[i]]=self.alpha*Object_Data[4]  

	def Training_the_Model(self,Table_For_Data_Updation):
		Table_For_Data_Updation.apply(self.Update_Prior_Probabilities_for_the_Given_Object,axis=1)
		Table_For_Data_Updation=self.Testing_the_Model(self.df_Train_Data_XY)
		return Table_For_Data_Updation

	def Construct_Bayesian_Model_and_Train(self,Epoch=100):
		Table_For_Updation_Train_Data=self.Create_the_Structure_of_the_Model()# strart Constructing the Model using training data set
		Train_Cost_Factor=round(1-len(Table_For_Updation_Train_Data)/len(self.df_Train_Data_XY),5)
		Best_Prior_Prob=self.Prior_Probabilities.copy()
		Best_Connection_Weights=self.Connection_Weights.copy()
		Largest_Train_Cost_Factor=Train_Cost_Factor
		for i in range(0,Epoch):
			if(Train_Cost_Factor<1):
				Table_For_Updation_Train_Data=self.Training_the_Model(Table_For_Updation_Train_Data)# up date the model
				Train_Cost_Factor=round(1-len(Table_For_Updation_Train_Data)/len(self.df_Train_Data_XY),5)
				if(Largest_Train_Cost_Factor<Train_Cost_Factor):
					Best_Prior_Prob=self.Prior_Probabilities.copy()
					Best_Connection_Weights=self.Connection_Weights.copy()
					Largest_Train_Cost_Factor=Train_Cost_Factor
		Latest_Model=[self.Connection_Pattern,self.Prior_Probabilities,self.Connection_Weights,self.Number_of_Class,self.Unique_Class_Names,self.Min_Feature_Values,self.Max_Feature_Values]
		Best_Model=[self.Connection_Pattern,Best_Prior_Prob,Best_Connection_Weights,self.Number_of_Class,self.Unique_Class_Names,self.Min_Feature_Values,self.Max_Feature_Values]
		return [Largest_Train_Cost_Factor,Train_Cost_Factor,Best_Model,Latest_Model]
    
#Prediction
	def Temp_Predict_Unknown_Object(self,Object_Features):  # only for Unknown_Data_Cost_Factor()    
		Object_Data=list((((Object_Features-self.Min_Feature_Values)/(self.Max_Feature_Values-self.Min_Feature_Values))*(self.Resolution-1)).round(0))
		Temp_Value=self.Find_Object_Likelihood_for_All_Class_for_an_Object(Object_Data)
		#Predicted_Class=Temp_Value[0][0]#Predicted_Class_Probability=Temp_Value[1][0]
		return [Temp_Value[0][0],Temp_Value[1][0]]


	def Unknown_Data_Cost_Factor(self,X_UnKnown,Y_UnKnown,Trained_Model):
		self.Connection_Pattern=Trained_Model[0]
		self.Prior_Probabilities=Trained_Model[1]
		self.Connection_Weights=Trained_Model[2]
		self.Number_of_Class=Trained_Model[3]
		self.Unique_Class_Names=Trained_Model[4]
		self.Min_Feature_Values=Trained_Model[5]
		self.Max_Feature_Values=Trained_Model[6] 
     
		df_X_UnKnown=pd.DataFrame(X_UnKnown)
		Data_UnKnown_Result=df_X_UnKnown.apply(self.Temp_Predict_Unknown_Object,axis=1)
		num=[1 for i in range(len(Y_UnKnown)) if(Data_UnKnown_Result[i][0]==Y_UnKnown[i])]
		return sum(num)/len(Y_UnKnown) 
###############

	def Predict_Single_Object(self,Object_Features,Trained_Model):  
		self.Connection_Pattern=Trained_Model[0]
		self.Prior_Probabilities=Trained_Model[1]
		self.Connection_Weights=Trained_Model[2]
		self.Number_of_Class=Trained_Model[3]
		self.Unique_Class_Names=Trained_Model[4]
		self.Min_Feature_Values=Trained_Model[5]
		self.Max_Feature_Values=Trained_Model[6]        
		Object_Data=list((((Object_Features-self.Min_Feature_Values)/(self.Max_Feature_Values-self.Min_Feature_Values))*(self.Resolution-1)).round(0))
		Temp_Value=self.Find_Object_Likelihood_for_All_Class_for_an_Object(Object_Data)
		return [Temp_Value[0][0],Temp_Value[1][0]]

#######################################################################    
class Bayesian_Model:
	def __init__(self,Resolution=4,Number_of_Feature_Connections=2,alpha=0.1):
		self.Resolution=Resolution
		self.Number_of_Feature_Connections=Number_of_Feature_Connections
		self.alpha=alpha 
        
	def fit(self,X_train,Y_train,Epoch):
		self.Bx1=Bayesian_Model_Training_and_Testing(X_train,Y_train,self.Resolution,self.Number_of_Feature_Connections,self.alpha)
		Train_Data=self.Bx1.Construct_Bayesian_Model_and_Train(Epoch)
		self.Best_Train_Cost_Factor=Train_Data[0]
		self.Latest_Train_Cost_Factor=Train_Data[1]
		self.Train_Cost_Factor=self.Best_Train_Cost_Factor
		self.Best_Model=Train_Data[2]
		self.Latest_Model=Train_Data[3]        

	def predict_data_set(self,X_test,Y_test):  
		self.Best_Test_Cost_Factor=self.Bx1.Unknown_Data_Cost_Factor(X_test,Y_test,self.Best_Model)
		self.Latest_Test_Cost_Factor=self.Bx1.Unknown_Data_Cost_Factor(X_test,Y_test,self.Latest_Model)
		if(self.Best_Test_Cost_Factor>self.Latest_Test_Cost_Factor):
			self.Test_Cost_Factor=self.Best_Test_Cost_Factor
		else:
			self.Test_Cost_Factor=self.Latest_Test_Cost_Factor
	def predict_object(self,Object_Features,Model="Best"):
		if(Model=="Best"):
			Predict_data=self.Bx1.Predict_Single_Object(Object_Features,self.Best_Model)
		elif(Model=="Lateest"):
			Predict_data=self.Bx1.Predict_Single_Object(Object_Features,self.Latest_Model)
		else:
			print("Error in selecting the Mode type ")
		return {"Predicted_class":Predict_data[0],"Level_of_confidence":Predict_data[1]}
####################################################################################################

class Bayesian_Model_PipeLine:    
	def __init__(self,Res_Lst=[2,3],NFtr_Con_Lst=[2,3],Alp_Lst=[0.1,0.2],Epoch=10):
		self.Res_Lst=Res_Lst
		self.NFtr_Con_Lst=NFtr_Con_Lst
		self.Alp_Lst=Alp_Lst
		self.Epoch=Epoch

	def JBPNN_Temp_Find_The_Best(self,RS):
		X_train,X_test,Y_train,Y_test=train_test_split(self.Data_X, self.Data_Y,test_size=0.2,stratify=self.Data_Y,shuffle=True,random_state=RS**4)
		Best_Test_CF=0
		for Res in self.Res_Lst:
#			print (RS,"\t",Res)
			for NOFCs in self.NFtr_Con_Lst:
				for alpha in self.Alp_Lst:
					BMx=Bayesian_Model(Res,NOFCs,alpha)
					BMx.fit(X_train,Y_train,self.Epoch)
					BMx.predict_data_set(X_test,Y_test)
					if((Best_Test_CF<BMx.Test_Cost_Factor) and ((BMx.Test_Cost_Factor-BMx.Train_Cost_Factor)<0.05)):
						Best_Test_CF=BMx.Test_Cost_Factor
						Best_Values=[RS,BMx.Test_Cost_Factor,BMx.Train_Cost_Factor,Res,NOFCs,alpha]
		del X_train,X_test,Y_train,Y_test
		return Best_Values

	def Estimator(self,Data_X,Data_Y,NTest=10):
		self.Data_X=Data_X
		self.Data_Y=Data_Y
		RS=list(range(1,NTest+1))
		with Pool() as pool:
			Best_Values=pool.map(self.Temp_Find_The_Best,RS)
		Best_Values=pd.DataFrame(Best_Values)
		Best_Values.columns=["RS","Best_Test_CF", "Best_Train_CF","Res","NOFCs","Alpha"]
		return Best_Values
