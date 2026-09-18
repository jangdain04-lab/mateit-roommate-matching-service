# forms.py
from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    SEMESTER_CHOICES = [
        ('1-1','1학년 1학기'), ('1-2','1학년 2학기'),
        ('2-1','2학년 1학기'), ('2-2','2학년 2학기'),
        ('3-1','3학년 1학기'), ('3-2','3학년 2학기'),
        ('4-1','4학년 1학기'), ('4-2','4학년 2학기'),
    ]
    BIRTHYEAR_CHOICES = [(str(y), str(y)) for y in range(1990, 2007)]
    GENDER_CHOICES = [('남성','남성'),('여성','여성')]
    DORM_CHOICES   = [('신기숙사','신기숙사'),('구기숙사','구기숙사')]

    semester   = forms.ChoiceField(choices=SEMESTER_CHOICES, label="학년/학기")
    birth_year = forms.ChoiceField(choices=BIRTHYEAR_CHOICES, label="출생년도")
    gender     = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.RadioSelect, label="성별")
    dorm_type  = forms.ChoiceField(choices=DORM_CHOICES,  widget=forms.RadioSelect, label="기숙사 종류")

    class Meta:
        model = UserProfile
        # user 필드는 View에서 채워주기 때문에 폼에서 제외
        exclude = ['user']
        # 나머지 필드 순서대로 
        fields = [
            'nickname', 'semester', 'birth_year', 'gender', 'dorm_type', 'intro_sentence',
            'daily_rhythm','wake_habit','weekend_life','sleep_habit','personality_type',
            'opinion_style','privacy_need','scent_sensitivity','earphone_use','preferred_temp',
            'cleaning_style','study_place','shower_time','shared_item_opinion',
            'outing_frequency','smoking','military',
        ]
        widgets = {
            'nickname':       forms.TextInput(attrs={'placeholder':'닉네임을 입력하세요'}),
            'intro_sentence': forms.Textarea(attrs={
                                  'placeholder':'나를 소개하는 짧은 문장을 입력하세요',
                                  'rows':3, 'maxlength':10
                                }),
            # 생활 스타일 항목들은 모두 라디오 형태로
            'daily_rhythm':      forms.RadioSelect(),
            'wake_habit':        forms.RadioSelect(),
            'weekend_life':      forms.RadioSelect(),
            'sleep_habit':       forms.RadioSelect(),
            'personality_type':  forms.RadioSelect(),
            'opinion_style':     forms.RadioSelect(),
            'privacy_need':      forms.RadioSelect(),
            'scent_sensitivity': forms.RadioSelect(),
            'earphone_use':      forms.RadioSelect(),
            'preferred_temp':    forms.RadioSelect(),
            'cleaning_style':    forms.RadioSelect(),
            'study_place':       forms.RadioSelect(),
            'shower_time':       forms.RadioSelect(),
            'shared_item_opinion': forms.RadioSelect(),
            'outing_frequency':  forms.RadioSelect(),
            'smoking':           forms.RadioSelect(),
            'military':          forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

        # 모든 필드를 기본적으로 required=True 설정
        for field in self.fields.values():
            field.required = True

        # 🔸 intro_sentence 글자 수 제한 (서버 측 검사용)
        self.fields['intro_sentence'].max_length = 10

        # 🔹 gender 값이 '여성'이면 military는 선택하지 않아도 되도록 함
        gender_val = self.data.get('gender') or self.initial.get('gender')
        if gender_val == '여성':
            self.fields['military'].required = False