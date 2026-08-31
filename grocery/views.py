from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import GroceryExpense
from .serializers import GroceryExpenseSerializer
from organizations.access import properties_accessible_to
from organizations.legacy import require_posted_property_access

class GroceryExpenseAPIView(APIView):
    # MultiPartParser is required to handle image/file uploads
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        """
        Fetch expenses. 
        Usage: /expenses/?property_id=1
        """
        property_id = request.query_params.get('property_id')
        
        if property_id:
            expenses = GroceryExpense.objects.filter(property_id=property_id, property__in=properties_accessible_to(request.user, 'billing.view')).order_by('-date')
        else:
            expenses = GroceryExpense.objects.filter(property__in=properties_accessible_to(request.user, 'billing.view')).order_by('-date')
            
        serializer = GroceryExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Create a new expense entry
        """
        require_posted_property_access(request, 'billing.manage')
        serializer = GroceryExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Log errors if validation fails (useful for debugging unique emails/required fields)
        print(serializer.errors) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroceryExpenseDetailAPIView(APIView):
    """
    Handles updating or deleting a specific bill
    """
    def get_object(self, pk, user):
        try:
            return GroceryExpense.objects.get(pk=pk, property__in=properties_accessible_to(user, 'billing.manage'))
        except GroceryExpense.DoesNotExist:
            return None

    def patch(self, request, pk):
        expense = self.get_object(pk, request.user)
        if not expense:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = GroceryExpenseSerializer(expense, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        expense = self.get_object(pk, request.user)
        if expense:
            expense.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)
